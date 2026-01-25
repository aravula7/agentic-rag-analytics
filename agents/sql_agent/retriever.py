"""Schema retriever using Chroma embeddings."""

import logging
import os
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings
from openai import OpenAI

logger = logging.getLogger(__name__)


class SchemaRetriever:
    """Retrieve relevant schema documentation from Chroma vector DB."""

    def __init__(
        self,
        chroma_host: str = "localhost",
        chroma_port: int = 8082,
        collection_name: str = "schema_embeddings",
        embedding_model: str = "text-embedding-3-small",
        openai_api_key: str = None,
        persist_directory: str = "./embeddings"
    ):
        """Initialize Schema Retriever.
        
        Args:
            chroma_host: Chroma server host
            chroma_port: Chroma server port
            collection_name: Name of Chroma collection
            embedding_model: OpenAI embedding model
            openai_api_key: OpenAI API key for embeddings
            persist_directory: Local directory for Chroma persistence
        """
        self.embedding_model = embedding_model
        self.openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None
        
        # Initialize Chroma client
        try:
            # Try connecting to Chroma server
            self.chroma_client = chromadb.HttpClient(
                host=chroma_host,
                port=chroma_port
            )
            logger.info(f"Connected to Chroma server at {chroma_host}:{chroma_port}")
        except Exception as e:
            logger.warning(f"Could not connect to Chroma server: {e}")
            # Fallback to persistent client
            self.chroma_client = chromadb.PersistentClient(path=persist_directory)
            logger.info(f"Using persistent Chroma client at {persist_directory}")
        
        # Get or create collection
        try:
            self.collection = self.chroma_client.get_collection(name=collection_name)
            logger.info(f"Loaded existing collection: {collection_name}")
        except Exception:
            logger.info(f"Collection {collection_name} not found, will be created when embeddings are loaded")
            self.collection = None

    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
        
        response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding

    def retrieve(self, query: str, top_k: int = 5) -> str:
        """Retrieve relevant schema context for a query.
        
        Args:
            query: User's natural language query
            top_k: Number of relevant chunks to retrieve
            
        Returns:
            Concatenated schema context string
        """
        if not self.collection:
            logger.warning("Collection not loaded, returning empty context")
            return ""
        
        try:
            # Generate query embedding
            query_embedding = self._get_embedding(query)
            
            # Query Chroma
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            # Extract and concatenate documents
            if results and results['documents']:
                documents = results['documents'][0]  # First query result
                context = "\n\n".join(documents)
                logger.info(f"Retrieved {len(documents)} schema chunks")
                return context
            else:
                logger.warning("No schema chunks retrieved")
                return ""
                
        except Exception as e:
            logger.error(f"Error retrieving schema context: {e}")
            return ""

    def get_table_context(self, table_names: List[str]) -> str:
        """Get schema context for specific tables.
        
        Args:
            table_names: List of table names
            
        Returns:
            Schema context for specified tables
        """
        if not self.collection:
            return ""
        
        try:
            # Query by metadata filter
            results = self.collection.get(
                where={"table": {"$in": table_names}}
            )
            
            if results and results['documents']:
                context = "\n\n".join(results['documents'])
                logger.info(f"Retrieved context for tables: {table_names}")
                return context
            else:
                return ""
                
        except Exception as e:
            logger.error(f"Error retrieving table context: {e}")
            return ""