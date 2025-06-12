import time
from locust import HttpUser, task, between
import random
import os
import io
from locust import events

BASE_URL = "http://localhost:8001" 

class DocumentUser(HttpUser):
    """
    A user class that simulates interactions with the document summarizer API.
    """
    host = BASE_URL
    wait_time = between(1, 5)

    _user_email = None
    _password = "testpassword" 
    _access_token = None
    _uploaded_document_id = None
    _document_title = None

    def on_start(self):
        """
        On start, each user attempts to register or log in.
        """
        user_id = str(random.randint(100000, 999999))
        self._user_email = f"testuser_{user_id}@example.com"
        self._document_title = f"Test_Document_{user_id}"

        register_data = {"email": self._user_email, "password": self._password}
        with self.client.post("/api/v1/auth/register", json=register_data, catch_response=True, name="/api/v1/auth/register") as response:
            if response.status_code == 201:
                print(f"User {self._user_email} registered successfully.")
                response.success()
                self.login()
            elif response.status_code == 409: 
                print(f"User {self._user_email} already exists, attempting login.")
                response.success()
                self.login()
            else:
                response.failure(f"Failed to register user: {response.status_code} - {response.text}")
                self._access_token = None

    def login(self):
        """
        Logs in the user and stores the access token.
        """
        login_data = {"username": self._user_email, "password": self._password}
        with self.client.post("/api/v1/auth/token", data=login_data, catch_response=True, name="/api/v1/auth/token") as response:
            if response.status_code == 200:
                try:
                    response_json = response.json()
                    self._access_token = response_json.get("access_token")
                    if self._access_token:
                        print(f"User {self._user_email} logged in. Token (first 50 chars): {self._access_token[:50]}...")
                        response.success()
                    else:
                        response.failure(f"Login successful (200 OK) but no 'access_token' in response for {self._user_email}. Full response: {response.text}")
                        self._access_token = None
                except Exception as e:
                    response.failure(f"Login successful (200 OK) but failed to parse JSON or extract token for {self._user_email}: {e}. Full response: {response.text}")
                    self._access_token = None
            else:
                response.failure(f"Failed to login user {self._user_email}: {response.status_code} - {response.text}")
                print(f"DEBUG: Login failed response for {self._user_email} (Status: {response.status_code}): {response.text}")
                self._access_token = None

    @task(3) # Task weight
    def upload_document_and_query(self):
        """
        Simulates uploading a document and then querying it.
        """
        if not self._access_token:
            print(f"Skipping upload for {self._user_email}: No access token.")
            return

        test_pdf_file_path = os.path.join(os.path.dirname(__file__), "test.pdf")
        pdf_content = None
        if os.path.exists(test_pdf_file_path):
            with open(test_pdf_file_path, "rb") as f:
                pdf_content = f.read()
        else:
            print(f"ERROR: 'test.pdf' not found at {test_pdf_file_path}. Please create a small 'test.pdf' file for realistic testing.")
            events.request.fire(
                request_type="POST",
                name="Upload Document (Missing PDF)",
                response_time=0,
                response_length=0,
                response=None, 
                exception=f"Missing 'test.pdf' file for upload simulation."
            )
            return

        files = {'file': (f'{self._document_title}.pdf', io.BytesIO(pdf_content), 'application/pdf')}
        data = {'title': self._document_title}
        headers = {'Authorization': f'Bearer {self._access_token}'}

        with self.client.post("/api/v1/documents/upload", files=files, data=data, headers=headers, catch_response=True, name="/api/v1/documents/upload") as response:
            if response.status_code == 201:
                self._uploaded_document_id = response.json().get("id")
                self._document_title = response.json().get("title")
                response.success()
                
                self.wait_for_processing_and_query() 
            else:
                response.failure(f"Failed to upload document for {self._user_email}: {response.status_code} - {response.text}")
                self._uploaded_document_id = None

    @task(1) 
    def get_documents_list(self):
        """
        Simulates fetching the list of documents.
        """
        if not self._access_token:
            print(f"Skipping get_documents_list for {self._user_email}: No access token.")
            return

        headers = {'Authorization': f'Bearer {self._access_token}'}
        with self.client.get("/api/v1/documents", headers=headers, catch_response=True, name="/api/v1/documents") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to fetch document list for {self._user_email}: {response.status_code} - {response.text}")

    def wait_for_processing_and_query(self):
        """
        Waits for a document to be processed and then queries it.
        This is a helper method, not a Locust @task.
        """
        if not self._uploaded_document_id or not self._access_token:
            return

        max_attempts = 30
        poll_interval = 2

        for i in range(max_attempts):
            time.sleep(poll_interval)
            headers = {'Authorization': f'Bearer {self._access_token}'}
            with self.client.get(f"/api/v1/documents/{self._uploaded_document_id}/processing_status", headers=headers, catch_response=True, name="/api/v1/documents/:id/processing_status") as status_response:
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    db_status = status_data.get("db_status")
                    if db_status == "completed":
                        status_response.success()
                        self.query_document_task()
                        return
                    elif db_status == "failed":
                        status_response.failure(f"Document {self._uploaded_document_id} processing failed: {status_data.get('celery_state', 'N/A')}")
                        return
                else:
                    status_response.failure(f"Failed to get status for document {self._uploaded_document_id}: {status_response.status_code}")
            
        print(f"Document {self._uploaded_document_id} processing timed out after {max_attempts * poll_interval} seconds.")
        events.request.fire(
            request_type="GET",
            name="Get Document Status (Timed Out)",
            response_time=(max_attempts * poll_interval * 1000),
            response_length=0, 
            response=None,
            exception=f"Processing timed out for document {self._uploaded_document_id}"
        )


    def query_document_task(self):
        """
        Simulates querying a document after it's processed.
        This is a helper method, not a Locust @task.
        """
        if not self._uploaded_document_id or not self._access_token:
            print("Skipping query: No document ID or token.")
            return

        query_text = "What is the main topic of the document?"
        headers = {'Authorization': f'Bearer {self._access_token}'}
        params = {"query_text": query_text}

        with self.client.get(f"/api/v1/documents/{self._uploaded_document_id}/query/", params=params, headers=headers, catch_response=True, name="/api/v1/documents/:id/query") as response:
            if response.status_code == 200:
                llm_answer = response.json().get("llm_answer")
                if llm_answer:
                    response.success()
                else:
                    response.failure(f"Query successful but no LLM answer: {response.text}")
            else:
                response.failure(f"Failed to query document {self._uploaded_document_id}: {response.status_code} - {response.text}")