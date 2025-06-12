# app/services/llm_service.py
import httpx
import logging
from typing import Optional, Dict, Any, List
from transformers import AutoTokenizer
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=settings.COLLEGE_LLM_ENDPOINT, timeout=60.0)
        self.tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-Instruct-v0.2")
        logger.info(f"LLMService initialized. Connecting to LLM at: {settings.COLLEGE_LLM_ENDPOINT}.")

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    def _words_to_tokens(self, words: int) -> int:
        return int(words * 1.3)
    
    async def generate_text(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> Optional[str]:
        if not self.client:
            logger.error("LLMService client not initialized.")
            return None
        
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "n": 1,
            "stop": ["User:", "###", "</s>"],
            "stream": False
        }

        try:
            response = await self.client.post("/generate", headers=headers, json=payload)
            response.raise_for_status()
            response_data = response.json()

            if "text" in response_data and isinstance(response_data["text"], list) and len(response_data["text"]) > 0:
                generated_text = response_data["text"][0]
                logger.info(f"Successfully generated text from LLM. Generated tokens: {self.count_tokens(generated_text)}")
                return generated_text.split("[/INST]")[1] if "[/INST]" in generated_text else generated_text
            else:
                logger.warning(f"Unexpected response format from LLM: {response_data}")
                return None
            
        except httpx.RequestError as e:
            logger.error(f"An error occurred while requesting LLM generation: {e}")
            return None
        
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM generation failed with status {e.response.status_code}: {e.response.text}")
            return None
        
        except Exception as e:
            logger.error(f"An unexpected error occurred during LLM generation: {e}")
            return None
        
    async def generate_summary(self, text_content: str, max_input_tokens: int = 30000,
                               words_per_chunk_summary: int = 100) -> Optional[str]:
        
        base_prompt_overhead_direct = self.count_tokens(
            "[INST] Provide a comprehensive and detailed summary of the following document. Cover all main points, key arguments, and the overall conclusion thoroughly. The summary should be easy to understand and provide a complete overview of the content.\n\nDocument:\n\nComprehensive Document Summary: [/INST]"
        )
        base_prompt_overhead_section = self.count_tokens(
            "[INST] Summarize the following section of a larger document. Focus on the main points and key information presented in this specific section. Ensure it is a self-contained summary of THIS section only. Do not provide a conclusion for the entire document or transition phrases that suggest continuation from previous sections. Do not mention the section of the document you are summarizing.\n\nSection X:\n\nSection X Summary: [/INST]"
        )
        base_prompt_overhead_reduce = self.count_tokens(
            "[INST] You have been provided with several summaries of different sections of a single large document. Your primary task is to synthesize these individual summaries into one comprehensive, detailed, and cohesive summary of the entire document. Crucially, remove all references to specific sections or chapters (e.g., \"In Section X\", \"Chapter Y discusses\"). Integrate the information smoothly as if it were a single narrative. Ensure a logical flow, integrate the main ideas from all sections, and avoid redundancy. Provide a thorough overview that captures the essence and key insights of the full content.\n\nSection Summaries:\n\nComprehensive Document Summary: [/INST]"
        )

        effective_content_limit_for_splitting = max_input_tokens - max(base_prompt_overhead_direct, base_prompt_overhead_section, base_prompt_overhead_reduce)
        
        if self.count_tokens(text_content) <= effective_content_limit_for_splitting:
            prompt = f"""[INST] Provide a comprehensive and detailed summary of the following document. Cover all main points, key arguments, and the overall conclusion thoroughly. The summary should be easy to understand and provide a complete overview of the content.

            Document:
            {text_content}

            Comprehensive Document Summary: [/INST]"""
            
            direct_summary_max_tokens = self._words_to_tokens(words_per_chunk_summary * 2) 
            logger.info("Generating direct summary (text fits token limit)...")
            summary = await self.generate_text(prompt, max_tokens=direct_summary_max_tokens)
            return summary
        else:
            logger.info("Text exceeds token limit. Initiating recursive summarization.")
            
            chunk_size_for_summarization = int(effective_content_limit_for_splitting * 0.8) 
            chunk_overlap_for_summarization = int(chunk_size_for_summarization * 0.1)

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size_for_summarization,
                chunk_overlap=chunk_overlap_for_summarization,
                length_function=self.count_tokens,
                is_separator_regex=False,
            )
            chunks = text_splitter.split_text(text_content)
            logger.info(f"Split document into {len(chunks)} chunks for summarization.")

            max_tokens_per_chunk_summary = self._words_to_tokens(words_per_chunk_summary)

            summaries = []
            for i, chunk in enumerate(chunks):
                chunk_summary_prompt = f"""[INST] Summarize the following section of a larger document. Focus on the main points and key information presented in this specific section. Ensure it is a self-contained summary of THIS section only. Do not provide a conclusion for the entire document or transition phrases that suggest continuation from previous sections. **Do not mention the section of the document you are summarizing (e.g., "In Section X").**

                Section {i+1}:
                {chunk}

                Section {i+1} Summary: [/INST]"""
                
                if self.count_tokens(chunk_summary_prompt) > max_input_tokens:
                    logger.warning(f"Chunk {i+1} with its prompt still exceeds max_input_tokens after initial splitting. This might lead to issues or requires further splitting. Skipping this chunk for summarization for now.")
                    continue 
                
                logger.info(f"Summarizing chunk {i+1}/{len(chunks)} with max_tokens={max_tokens_per_chunk_summary}...")
                chunk_summary = await self.generate_text(chunk_summary_prompt, max_tokens=max_tokens_per_chunk_summary)
                if chunk_summary:
                    summaries.append(chunk_summary)
                else:
                    logger.warning(f"Failed to generate summary for chunk {i+1}.")

            if not summaries:
                logger.error("No summaries generated for any chunk.")
                return None

            combined_summaries_text = "\n\n".join(summaries) 
            logger.info(f"\nCombined summaries length (tokens): {self.count_tokens(combined_summaries_text)}")
            
            if self.count_tokens(combined_summaries_text) > effective_content_limit_for_splitting:
                logger.info("Combined chunk summaries still exceed token limit. Recursively summarizing summaries.")
                final_summary = await self.generate_summary(
                    combined_summaries_text, 
                    max_input_tokens=max_input_tokens, 
                    words_per_chunk_summary=words_per_chunk_summary
                )
                return final_summary
            else:
                final_reduce_prompt = f"""[INST] You have been provided with several summaries of different sections of a single large document.

                Your primary task is to **synthesize these individual summaries into one comprehensive, detailed, and cohesive summary of the entire document.**

                **Crucially, remove all references to specific sections or chapters (e.g., \"In Section X\", \"Chapter Y discusses\"). Integrate the information smoothly as if it were a single narrative.**

                Ensure a logical flow, integrate the main ideas from all sections, and avoid redundancy. Provide a thorough overview that captures the essence and key insights of the full content.

                Section Summaries:
                {combined_summaries_text}

                Comprehensive Document Summary: [/INST]"""
                
                desired_total_summary_words = len(chunks) * words_per_chunk_summary
                max_final_summary_tokens_cap = 3000 
                
                final_summary_max_tokens = min(self._words_to_tokens(desired_total_summary_words), max_final_summary_tokens_cap)

                logger.info(f"Generating final summary from combined chunk summaries with max_tokens={final_summary_max_tokens}...")
                final_summary = await self.generate_text(final_reduce_prompt, max_tokens=final_summary_max_tokens)
                parts = final_summary.rsplit('.', 1)
                return parts[0].strip() + "."

llm_service = LLMService()