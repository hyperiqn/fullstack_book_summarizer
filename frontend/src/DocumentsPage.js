import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaBook, FaPlus, FaSignOutAlt, FaPaperPlane, FaSpinner, FaTrash } from 'react-icons/fa';
import { DotLoader } from 'react-spinners';
import axios from 'axios';

const normalizeDocumentForComparison = (doc) => {
  const newDoc = { ...doc };
  delete newDoc.upload_timestamp;
  return newDoc;
};

function DocumentsPage() {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState([]);
  const documentsRef = useRef(documents);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [loadingDocuments, setLoadingDocuments] = useState(false);
  const [initialLoadComplete, setInitialLoadComplete] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  const [isChatting, setIsChatting] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const chatEndRef = useRef(null);
  const [newDocumentTitle, setNewDocumentTitle] = useState('');
  const [deletingDocId, setDeletingDocId] = useState(null); 

  const API_BASE_URL = 'http://localhost:8001/api/v1';

  useEffect(() => {
    documentsRef.current = documents;
  }, [documents]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  useEffect(() => {
    if (selectedDocument) {
      try {
        const storedMessages = localStorage.getItem(`chatMessages_doc_${selectedDocument.id}`);
        if (storedMessages) {
          setChatMessages(JSON.parse(storedMessages));
        } else {
          setChatMessages([]);
        }
      } catch (e) {
        console.error("Failed to load chat messages from localStorage:", e);
        setChatMessages([]);
      }
    } else {
      setChatMessages([]);
    }
  }, [selectedDocument]);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('access_token');
    return {
      'Authorization': `Bearer ${token}`,
      'Accept': 'application/json',
    };
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    navigate('/login');
  };

  const fetchDocumentsInternal = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/documents`, { headers: getAuthHeaders() });
      const newDocuments = Array.isArray(response.data) ? response.data : [];

      const sortedNewDocuments = newDocuments.sort((a, b) => new Date(b.upload_timestamp) - new Date(a.upload_timestamp));

      const normalizedCurrentDocuments = documentsRef.current.map(normalizeDocumentForComparison);
      const normalizedFetchedDocuments = sortedNewDocuments.map(normalizeDocumentForComparison);


      if (JSON.stringify(normalizedFetchedDocuments) !== JSON.stringify(normalizedCurrentDocuments)) {
        setDocuments(sortedNewDocuments);
        setMessage('');
      } else {
        // console.log('Documents state NOT UPDATING (data is the same based on normalized comparison).');
      }
    } catch (error) {
      console.error('Error fetching documents:', error);
      setMessage('Failed to load documents. Please log in again.');
      if (error.response && error.response.status === 401) {
        handleLogout();
      }
    } finally {
      if (!initialLoadComplete) {
        setInitialLoadComplete(true);
      }
      setLoadingDocuments(false);
    }
  };

  useEffect(() => {
    if (!initialLoadComplete) {
        setLoadingDocuments(true);
    }
    fetchDocumentsInternal();

    const intervalId = setInterval(() => {
        fetchDocumentsInternal();
    }, 5000);

    return () => clearInterval(intervalId);
  }, [initialLoadComplete]); 


  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (!newDocumentTitle.trim()) {
      setMessage('Please enter a title for the book.');
      return;
    }

    setUploading(true);
    setMessage('');
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', newDocumentTitle.trim());

    try {
      const response = await axios.post(`${API_BASE_URL}/documents/upload`, formData, {
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'multipart/form-data', 
        },
      });
      setMessage('Book uploaded successfully! Processing...');
      setNewDocumentTitle('');
      setSelectedDocument(response.data);
      setChatMessages([]);
      setIsChatting(false);
    } catch (error) {
      console.error('Error uploading file:', error);
      setMessage(`File upload failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setUploading(false);
      event.target.value = '';
    }
  };

  const handleDocumentClick = (doc) => {
    setSelectedDocument(doc);
    setIsChatting(false);
  };

  const handleSendMessage = async () => {
    if (!chatInput.trim() || !selectedDocument) return;

    const userMessage = { sender: 'user', text: chatInput };
    setChatMessages((prevMessages) => {
      const updatedMessages = [...prevMessages, userMessage];
      localStorage.setItem(`chatMessages_doc_${selectedDocument.id}`, JSON.stringify(updatedMessages));
      return updatedMessages;
    });
    setChatInput('');
    setChatLoading(true);

    try {
      const response = await axios.get(`${API_BASE_URL}/documents/${selectedDocument.id}/query/`, {
        headers: getAuthHeaders(),
        params: { query_text: chatInput }
      });

      const aiMessage = { sender: 'ai', text: response.data.llm_answer };
      setChatMessages((prevMessages) => {
        const updatedMessages = [...prevMessages, aiMessage];
        localStorage.setItem(`chatMessages_doc_${selectedDocument.id}`, JSON.stringify(updatedMessages));
        return updatedMessages;
      });
    } catch (error) {
      console.error('Error sending message:', error);
      setChatMessages((prevMessages) => {
        const errorMessages = [...prevMessages, { sender: 'ai', text: `Error: ${error.response?.data?.detail || 'Failed to get response.'}` }];
        localStorage.setItem(`chatMessages_doc_${selectedDocument.id}`, JSON.stringify(errorMessages));
        return errorMessages;
      });
    } finally {
      setChatLoading(false);
    }
  };

  const handleDeleteDocument = async (documentId) => {
    if (!window.confirm("Are you sure you want to delete this book? This action cannot be undone.")) {
      return;
    }

    setDeletingDocId(documentId);
    setMessage(''); 

    try {
      await axios.delete(`${API_BASE_URL}/documents/${documentId}`, { headers: getAuthHeaders() });
      setMessage('Book deleted successfully!');
      setDocuments(prevDocs => prevDocs.filter(doc => doc.id !== documentId));
      if (selectedDocument && selectedDocument.id === documentId) {
        setSelectedDocument(null); 
        localStorage.removeItem(`chatMessages_doc_${documentId}`); 
      }
    } catch (error) {
      console.error('Error deleting document:', error);
      setMessage(`Failed to delete book: ${error.response?.data?.detail || error.message}`);
      if (error.response && error.response.status === 401) {
        handleLogout();
      }
    } finally {
      setDeletingDocId(null); 
    }
  };

  const toggleChatView = (isChat) => {
    setIsChatting(isChat);
  };

  return (
    <div className="flex h-screen bg-gray-100 font-sans text-gray-800">
      {/* Sidebar */}
      <aside className="w-64 bg-white p-6 shadow-md flex flex-col justify-between">
        <div>
          <div className="flex items-center mb-8">
            <FaBook className="text-blue-600 text-3xl mr-3" />
            <h1 className="text-2xl font-bold text-gray-800">Summarizer</h1>
          </div>

          {/* New Title Input Field */}
          <input
            type="text"
            placeholder="Enter book title (e.g., 'My Great Novel')"
            value={newDocumentTitle}
            onChange={(e) => setNewDocumentTitle(e.target.value)}
            className="w-full p-2 mb-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
            disabled={uploading}
          />

          {/* Upload Button */}
          <label htmlFor="file-upload" className="flex items-center justify-center p-3 mb-6 bg-blue-600 text-white rounded-lg shadow-md cursor-pointer hover:bg-blue-700 transition-colors">
            {uploading ? <FaSpinner className="animate-spin mr-2" /> : <FaPlus className="mr-2" />}
            {uploading ? 'Uploading...' : 'Upload New Book'}
            <input id="file-upload" type="file" accept=".pdf,.epub,.txt" onChange={handleFileUpload} className="hidden" disabled={uploading} />
          </label>

          {message && (
            <p className={`text-sm mb-4 ${message.includes('Error') || message.includes('failed') ? 'text-red-500' : 'text-green-600'}`}>
              {message}
            </p>
          )}

          <h2 className="text-md font-semibold text-gray-600 mb-4 uppercase tracking-wider">My Books</h2>
          <ul className="space-y-3 max-h-[calc(100vh-350px)] overflow-y-auto pr-2 custom-scrollbar">
            {initialLoadComplete ? (
              (Array.isArray(documents) && documents.length === 0) ? (
                <li className="text-sm text-gray-500 text-center py-4">No books uploaded yet.</li>
              ) : (
                documents.map((doc) => (
                  <li
                    key={doc.id}
                    className={`p-3 rounded-lg text-sm cursor-pointer transition-colors duration-200 flex items-center justify-between group ${
                      selectedDocument?.id === doc.id ? 'bg-blue-100 text-blue-800 font-semibold' : 'hover:bg-gray-50 text-gray-700'
                    }`}
                  >
                    <span onClick={() => handleDocumentClick(doc)} className="flex-1 truncate pr-2">
                      {doc.title}
                    </span>
                    <div className="flex items-center space-x-2">
                      {doc.processing_status === 'processing' && (
                        <FaSpinner className="animate-spin text-blue-500" title="Processing..." />
                      )}
                      {doc.processing_status === 'failed' && (
                        <span className="text-red-500 text-xs" title="Processing failed">Failed</span>
                      )}
                      {/* Delete Button */}
                      <button
                        onClick={(e) => { 
                            e.stopPropagation();
                            handleDeleteDocument(doc.id);
                        }}
                        className="text-gray-400 hover:text-red-600 p-1 rounded-full transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                        title="Delete Book"
                        disabled={deletingDocId === doc.id} 
                      >
                        {deletingDocId === doc.id ? <FaSpinner className="animate-spin" /> : <FaTrash />}
                      </button>
                    </div>
                  </li>
                ))
              )
            ) : (
              <li className="text-center py-4">
                <DotLoader color="#3B82F6" size={20} />
                <p className="text-sm text-gray-500 mt-2">Loading books...</p>
              </li>
            )}
          </ul>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center justify-center p-3 bg-red-600 text-white rounded-lg shadow-md hover:bg-red-700 transition-colors"
        >
          <FaSignOutAlt className="mr-2" />
          Logout
        </button>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col bg-gray-50 p-6">
        {!selectedDocument ? (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-500">
            <FaBook className="text-6xl mb-4" />
            <p className="text-lg">Select a book from the left to view its summary or chat.</p>
            <p className="text-sm">Or upload a new one!</p>
          </div>
        ) : (
          <div className="flex-1 flex flex-col h-full">
            {/* Header for Document/Chat View */}
            <div className="flex items-center justify-between pb-4 border-b border-gray-200 mb-4">
              <div>
                <h2 className="text-2xl font-bold text-gray-800">{selectedDocument.title}</h2>
                <p className="text-sm text-gray-500">Unknown Author</p>
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={() => toggleChatView(false)}
                  className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${!isChatting ? 'bg-blue-600 text-white shadow-md' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
                >
                  Summary
                </button>
                <button
                  onClick={() => toggleChatView(true)}
                  className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${isChatting ? 'bg-blue-600 text-white shadow-md' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
                >
                  Chat
                </button>
              </div>
            </div>

            {/* Content Area (Summary or Chat) */}
            <div className="flex-1 overflow-y-auto pr-4 custom-scrollbar">
              {isChatting ? (
                // Chat View
                <div className="flex flex-col h-full">
                  <div className="flex-1 overflow-y-auto space-y-4 p-2">
                    {chatMessages.length === 0 && !chatLoading && (
                        <p className="text-center text-gray-500 text-sm py-4">Start chatting about this book!</p>
                    )}
                    {chatMessages.map((msg, index) => (
                      <div key={index} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div
                          className={`max-w-md p-3 rounded-lg shadow-sm text-sm ${
                            msg.sender === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-800'
                          }`}
                        >
                          {msg.text}
                        </div>
                      </div>
                    ))}
                    {chatLoading && (
                        <div className="flex justify-start">
                            <div className="max-w-md p-3 rounded-lg shadow-sm bg-gray-200 text-gray-800 text-sm">
                                <DotLoader color="#3B82F6" size={15} />
                            </div>
                        </div>
                    )}
                    <div ref={chatEndRef} /> {/* Scroll target */}
                  </div>
                  {/* Chat Input */}
                  <div className="mt-4 flex items-center border-t border-gray-200 pt-4">
                    <input
                      type="text"
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      onKeyPress={(e) => { if (e.key === 'Enter') handleSendMessage(); }}
                      placeholder="Ask a question about the book..."
                      className="flex-1 p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm mr-2"
                      disabled={chatLoading || selectedDocument.processing_status !== 'completed'}
                    />
                    <button
                      onClick={handleSendMessage}
                      className="p-3 bg-blue-600 text-white rounded-lg shadow-md hover:bg-blue-700 transition-colors disabled:opacity-50"
                      disabled={chatLoading || selectedDocument.processing_status !== 'completed'}
                    >
                      <FaPaperPlane />
                    </button>
                  </div>
                </div>
              ) : (
                // Summary View
                <div className="flex flex-col h-full p-4 bg-white rounded-lg shadow-sm">
                  <h3 className="text-xl font-semibold mb-4 border-b pb-2 text-gray-700">Summary</h3>
                  {selectedDocument.processing_status === 'completed' && selectedDocument.summary ? (
                    <p className="text-gray-700 leading-relaxed text-sm">{selectedDocument.summary}</p>
                  ) : selectedDocument.processing_status === 'processing' ? (
                    <div className="flex flex-col items-center justify-center text-gray-500 text-center py-8">
                      <DotLoader color="#3B82F6" size={30} />
                      <p className="mt-4 text-sm">Book is still processing...</p>
                      <p className="text-xs">Summary will appear here when ready.</p>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center text-gray-500 text-center py-8">
                        <p className="text-sm">No summary available yet.</p>
                        <p className="text-xs">It might still be processing, or summary generation is not enabled.</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default DocumentsPage;