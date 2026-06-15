# rag/knowledge_base.py - RAG implementation with ChromaDB and sentence-transformers
import os
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import json

# Initialize the embedding model
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

class KnowledgeBase:
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Initialize the knowledge base with ChromaDB and sentence transformers.
        
        Args:
            persist_directory: Directory to store ChromaDB data
        """
        self.persist_directory = persist_directory
        
        # Create ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Create collection - we'll use the default embedding function
        try:
            self.collection = self.client.get_or_create_collection(name="runbooks")
        except Exception:
            # If that fails, create with explicit settings
            self.collection = self.client.create_collection(name="runbooks")
        
        # Create sample runbooks
        self.sample_runbooks = self._create_sample_runbooks()
        self._initialize_database()
    
    def _create_sample_runbooks(self) -> List[Dict[str, Any]]:
        """Create 6-8 sample runbooks for the telecom NOC context."""
        return [
            {
                "id": "bgp_peer_down",
                "title": "BGP Peer Down",
                "symptom": "BGP peer goes down",
                "possible_causes": [
                    "Physical link failure",
                    "Configuration mismatch",
                    "Resource exhaustion on router"
                ],
                "resolution_steps": [
                    "Check physical connectivity",
                    "Verify BGP configuration",
                    "Monitor resource usage",
                    "Clear BGP session if appropriate"
                ],
                "category": "network",
                "severity": "critical"
            },
            {
                "id": "router_reboot",
                "title": "Router Reboot Required",
                "symptom": "Router unresponsive or crashing",
                "possible_causes": [
                    "Software bug",
                    "Resource exhaustion",
                    "Hardware failure"
                ],
                "resolution_steps": [
                    "Check system logs",
                    "Verify uptime and resource usage",
                    "Perform graceful reboot",
                    "Document the event"
                ],
                "category": "hardware",
                "severity": "critical"
            },
            {
                "id": "packet_loss",
                "title": "Packet Loss Detected",
                "symptom": "High packet loss on network links",
                "possible_causes": [
                    "Link congestion",
                    "Interface hardware issues",
                    "Routing problems"
                ],
                "resolution_steps": [
                    "Check interface statistics",
                    "Monitor traffic patterns",
                    "Restart interface if needed",
                    "Investigate underlying routing issues"
                ],
                "category": "network",
                "severity": "major"
            },
            {
                "id": "link_down",
                "title": "Link Down",
                "symptom": "Network link goes down",
                "possible_causes": [
                    "Physical cable disconnection",
                    "Interface hardware failure",
                    "Power outage"
                ],
                "resolution_steps": [
                    "Check physical connections",
                    "Verify interface status",
                    "Restart interface if needed",
                    "Check for hardware failures"
                ],
                "category": "hardware",
                "severity": "major"
            },
            {
                "id": "cpu_utilization_high",
                "title": "High CPU Utilization",
                "symptom": "Router CPU utilization exceeds threshold",
                "possible_causes": [
                    "CPU-intensive process",
                    "Memory leak",
                    "Network traffic spike"
                ],
                "resolution_steps": [
                    "Identify high CPU processes",
                    "Monitor memory usage",
                    "Clear cache if applicable",
                    "Consider load balancing"
                ],
                "category": "capacity",
                "severity": "major"
            },
            {
                "id": "memory_exhaustion",
                "title": "Memory Exhaustion",
                "symptom": "Router memory usage near capacity",
                "possible_causes": [
                    "Memory leak in software",
                    "Insufficient memory allocation",
                    "Large traffic bursts"
                ],
                "resolution_steps": [
                    "Check memory usage patterns",
                    "Restart memory-hungry processes",
                    "Clear buffers and caches",
                    "Consider hardware upgrade"
                ],
                "category": "capacity",
                "severity": "major"
            },
            {
                "id": "bgp_session_flap",
                "title": "BGP Session Flapping",
                "symptom": "BGP session repeatedly goes up and down",
                "possible_causes": [
                    "Unstable link",
                    "Configuration inconsistency",
                    "Timing issues in session negotiation"
                ],
                "resolution_steps": [
                    "Check link stability",
                    "Verify BGP configurations",
                    "Adjust session timers if needed",
                    "Clear sessions and monitor"
                ],
                "category": "network",
                "severity": "minor"
            },
            {
                "id": "dhcp_server_outage",
                "title": "DHCP Server Outage",
                "symptom": "DHCP service unavailable for clients",
                "possible_causes": [
                    "DHCP service crash",
                    "Network connectivity issues",
                    "Configuration errors"
                ],
                "resolution_steps": [
                    "Restart DHCP service",
                    "Check network connectivity",
                    "Verify configuration files",
                    "Monitor lease assignments"
                ],
                "category": "software",
                "severity": "minor"
            }
        ]
    
    def _initialize_database(self):
        """Initialize the database with sample runbooks."""
        try:
            # Check if collection is empty
            if self.collection.count() == 0:
                print("Initializing knowledge base with sample runbooks...")
                
                # Convert runbooks to text format for indexing
                documents = []
                metadatas = []
                ids = []
                
                for runbook in self.sample_runbooks:
                    # Create a rich text document combining all information
                    doc_text = f"""
                    Title: {runbook['title']}
                    Symptom: {runbook['symptom']}
                    Category: {runbook['category']}
                    Severity: {runbook['severity']}
                    
                    Possible Causes:
                    {' '.join(f'- {cause}' for cause in runbook['possible_causes'])}
                    
                    Resolution Steps:
                    {' '.join(f'- {step}' for step in runbook['resolution_steps'])}
                    """
                    
                    documents.append(doc_text.strip())
                    metadatas.append({
                        "title": runbook['title'],
                        "symptom": runbook['symptom'],
                        "category": runbook['category'],
                        "severity": runbook['severity'],
                        "id": runbook['id']
                    })
                    ids.append(runbook['id'])
                
                # Add documents to ChromaDB (if collection is empty)
                if len(documents) > 0:
                    self.collection.add(
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                    print(f"Added {len(self.sample_runbooks)} sample runbooks to knowledge base")
            else:
                print(f"Knowledge base already initialized with {self.collection.count()} runbooks")
                
        except Exception as e:
            print(f"Error initializing knowledge base: {e}")
    
    def add_runbook(self, title: str, symptom: str, possible_causes: List[str], 
                   resolution_steps: List[str], category: str, severity: str) -> str:
        """
        Add a new runbook to the knowledge base.
        
        Args:
            title: Runbook title
            symptom: Problem symptom
            possible_causes: List of possible causes
            resolution_steps: List of resolution steps
            category: Runbook category (network, hardware, etc.)
            severity: Severity level
            
        Returns:
            ID of the added runbook
        """
        # Create document text
        doc_text = f"""
        Title: {title}
        Symptom: {symptom}
        Category: {category}
        Severity: {severity}
        
        Possible Causes:
        {' '.join(f'- {cause}' for cause in possible_causes)}
        
        Resolution Steps:
        {' '.join(f'- {step}' for step in resolution_steps)}
        """
        
        # Generate unique ID
        import uuid
        runbook_id = str(uuid.uuid4())
        
        # Add to collection
        self.collection.add(
            documents=[doc_text.strip()],
            metadatas=[{
                "title": title,
                "symptom": symptom,
                "category": category,
                "severity": severity,
                "id": runbook_id
            }],
            ids=[runbook_id]
        )
        
        print(f"Added new runbook: {title}")
        return runbook_id
    
    def retrieve_runbooks(self, query: str, k: int = 3) -> str:
        """
        Retrieve relevant runbooks based on a query.
        
        Args:
            query: Query string to search for relevant runbooks
            k: Number of top results to return
            
        Returns:
            Formatted string of retrieved runbooks
        """
        try:
            # Perform similarity search
            results = self.collection.query(
                query_texts=[query],
                n_results=min(k, self.collection.count()),
                include=["documents", "metadatas"]
            )
            
            # Format results
            if len(results['documents'][0]) > 0:
                formatted_results = []
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i]
                    formatted_result = f"""
Runbook: {metadata['title']}
Symptom: {metadata['symptom']}
Category: {metadata['category']}
Severity: {metadata['severity']}

{doc}
                    """.strip()
                    formatted_results.append(formatted_result)
                
                return "\n\n---\n\n".join(formatted_results)
            else:
                return "No relevant runbooks found for the given query."
                
        except Exception as e:
            print(f"Error retrieving runbooks: {e}")
            return "Error retrieving runbooks."
    
    def get_all_runbooks_metadata(self) -> List[Dict]:
        """
        Get metadata for all runbooks in the knowledge base.
        
        Returns:
            List of runbook metadata dictionaries
        """
        try:
            all_docs = self.collection.get(include=["metadatas"])
            return all_docs["metadatas"]
        except Exception as e:
            print(f"Error getting runbooks metadata: {e}")
            return []

# Global instance
knowledge_base = None

def get_knowledge_base():
    """Get or create global knowledge base instance."""
    global knowledge_base
    if knowledge_base is None:
        knowledge_base = KnowledgeBase()
    return knowledge_base

def retrieve_runbooks(query: str, k: int = 3) -> str:
    """
    Retrieve relevant runbooks for a query using the knowledge base.
    
    Args:
        query: Query string to search for relevant runbooks
        k: Number of top results to return
        
    Returns:
        Formatted string of retrieved runbooks
    """
    kb = get_knowledge_base()
    return kb.retrieve_runbooks(query, k)

def create_knowledge_base(persist_directory: str = "./chroma_db") -> KnowledgeBase:
    """
    Create and initialize a new knowledge base.
    
    Args:
        persist_directory: Directory to store ChromaDB data
        
    Returns:
        Initialized KnowledgeBase instance
    """
    return KnowledgeBase(persist_directory)

# Example usage
if __name__ == "__main__":
    # Test the knowledge base
    kb = create_knowledge_base()
    
    # Test retrieval
    query = "Router CPU utilization going high"
    result = retrieve_runbooks(query, 2)
    print("Retrieved runbooks:")
    print(result)
    
    def _create_sample_runbooks(self) -> List[Dict[str, Any]]:
        """Create 6-8 sample runbooks for the telecom NOC context."""
        return [
            {
                "id": "bgp_peer_down",
                "title": "BGP Peer Down",
                "symptom": "BGP peer goes down",
                "possible_causes": [
                    "Physical link failure",
                    "Configuration mismatch",
                    "Resource exhaustion on router"
                ],
                "resolution_steps": [
                    "Check physical connectivity",
                    "Verify BGP configuration",
                    "Monitor resource usage",
                    "Clear BGP session if appropriate"
                ],
                "category": "network",
                "severity": "critical"
            },
            {
                "id": "router_reboot",
                "title": "Router Reboot Required",
                "symptom": "Router unresponsive or crashing",
                "possible_causes": [
                    "Software bug",
                    "Resource exhaustion",
                    "Hardware failure"
                ],
                "resolution_steps": [
                    "Check system logs",
                    "Verify uptime and resource usage",
                    "Perform graceful reboot",
                    "Document the event"
                ],
                "category": "hardware",
                "severity": "critical"
            },
            {
                "id": "packet_loss",
                "title": "Packet Loss Detected",
                "symptom": "High packet loss on network links",
                "possible_causes": [
                    "Link congestion",
                    "Interface hardware issues",
                    "Routing problems"
                ],
                "resolution_steps": [
                    "Check interface statistics",
                    "Monitor traffic patterns",
                    "Restart interface if needed",
                    "Investigate underlying routing issues"
                ],
                "category": "network",
                "severity": "major"
            },
            {
                "id": "link_down",
                "title": "Link Down",
                "symptom": "Network link goes down",
                "possible_causes": [
                    "Physical cable disconnection",
                    "Interface hardware failure",
                    "Power outage"
                ],
                "resolution_steps": [
                    "Check physical connections",
                    "Verify interface status",
                    "Restart interface if needed",
                    "Check for hardware failures"
                ],
                "category": "hardware",
                "severity": "major"
            },
            {
                "id": "cpu_utilization_high",
                "title": "High CPU Utilization",
                "symptom": "Router CPU utilization exceeds threshold",
                "possible_causes": [
                    "CPU-intensive process",
                    "Memory leak",
                    "Network traffic spike"
                ],
                "resolution_steps": [
                    "Identify high CPU processes",
                    "Monitor memory usage",
                    "Clear cache if applicable",
                    "Consider load balancing"
                ],
                "category": "capacity",
                "severity": "major"
            },
            {
                "id": "memory_exhaustion",
                "title": "Memory Exhaustion",
                "symptom": "Router memory usage near capacity",
                "possible_causes": [
                    "Memory leak in software",
                    "Insufficient memory allocation",
                    "Large traffic bursts"
                ],
                "resolution_steps": [
                    "Check memory usage patterns",
                    "Restart memory-hungry processes",
                    "Clear buffers and caches",
                    "Consider hardware upgrade"
                ],
                "category": "capacity",
                "severity": "major"
            },
            {
                "id": "bgp_session_flap",
                "title": "BGP Session Flapping",
                "symptom": "BGP session repeatedly goes up and down",
                "possible_causes": [
                    "Unstable link",
                    "Configuration inconsistency",
                    "Timing issues in session negotiation"
                ],
                "resolution_steps": [
                    "Check link stability",
                    "Verify BGP configurations",
                    "Adjust session timers if needed",
                    "Clear sessions and monitor"
                ],
                "category": "network",
                "severity": "minor"
            },
            {
                "id": "dhcp_server_outage",
                "title": "DHCP Server Outage",
                "symptom": "DHCP service unavailable for clients",
                "possible_causes": [
                    "DHCP service crash",
                    "Network connectivity issues",
                    "Configuration errors"
                ],
                "resolution_steps": [
                    "Restart DHCP service",
                    "Check network connectivity",
                    "Verify configuration files",
                    "Monitor lease assignments"
                ],
                "category": "software",
                "severity": "minor"
            }
        ]
    
    def _initialize_database(self):
        """Initialize the database with sample runbooks."""
        try:
            # Check if collection is empty
            if self.collection.count() == 0:
                print("Initializing knowledge base with sample runbooks...")
                
                # Convert runbooks to text format for indexing
                documents = []
                metadatas = []
                ids = []
                
                for runbook in self.sample_runbooks:
                    # Create a rich text document combining all information
                    doc_text = f"""
                    Title: {runbook['title']}
                    Symptom: {runbook['symptom']}
                    Category: {runbook['category']}
                    Severity: {runbook['severity']}
                    
                    Possible Causes:
                    {' '.join(f'- {cause}' for cause in runbook['possible_causes'])}
                    
                    Resolution Steps:
                    {' '.join(f'- {step}' for step in runbook['resolution_steps'])}
                    """
                    
                    documents.append(doc_text.strip())
                    metadatas.append({
                        "title": runbook['title'],
                        "symptom": runbook['symptom'],
                        "category": runbook['category'],
                        "severity": runbook['severity'],
                        "id": runbook['id']
                    })
                    ids.append(runbook['id'])
                
                # Add documents to ChromaDB
                self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                print(f"Added {len(self.sample_runbooks)} sample runbooks to knowledge base")
            else:
                print(f"Knowledge base already initialized with {self.collection.count()} runbooks")
                
        except Exception as e:
            print(f"Error initializing knowledge base: {e}")
    
    def add_runbook(self, title: str, symptom: str, possible_causes: List[str], 
                   resolution_steps: List[str], category: str, severity: str) -> str:
        """
        Add a new runbook to the knowledge base.
        
        Args:
            title: Runbook title
            symptom: Problem symptom
            possible_causes: List of possible causes
            resolution_steps: List of resolution steps
            category: Runbook category (network, hardware, etc.)
            severity: Severity level
            
        Returns:
            ID of the added runbook
        """
        # Create document text
        doc_text = f"""
        Title: {title}
        Symptom: {symptom}
        Category: {category}
        Severity: {severity}
        
        Possible Causes:
        {' '.join(f'- {cause}' for cause in possible_causes)}
        
        Resolution Steps:
        {' '.join(f'- {step}' for step in resolution_steps)}
        """
        
        # Generate unique ID
        import uuid
        runbook_id = str(uuid.uuid4())
        
        # Add to collection
        self.collection.add(
            documents=[doc_text.strip()],
            metadatas=[{
                "title": title,
                "symptom": symptom,
                "category": category,
                "severity": severity,
                "id": runbook_id
            }],
            ids=[runbook_id]
        )
        
        print(f"Added new runbook: {title}")
        return runbook_id
    
    def retrieve_runbooks(self, query: str, k: int = 3) -> str:
        """
        Retrieve relevant runbooks based on a query.
        
        Args:
            query: Query string to search for relevant runbooks
            k: Number of top results to return
            
        Returns:
            Formatted string of retrieved runbooks
        """
        try:
            # Perform similarity search
            results = self.collection.query(
                query_texts=[query],
                n_results=k,
                include=["documents", "metadatas"]
            )
            
            # Format results
            if len(results['documents'][0]) > 0:
                formatted_results = []
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i]
                    formatted_result = f"""
Runbook: {metadata['title']}
Symptom: {metadata['symptom']}
Category: {metadata['category']}
Severity: {metadata['severity']}

{doc}
                    """.strip()
                    formatted_results.append(formatted_result)
                
                return "\n\n---\n\n".join(formatted_results)
            else:
                return "No relevant runbooks found for the given query."
                
        except Exception as e:
            print(f"Error retrieving runbooks: {e}")
            return "Error retrieving runbooks."
    
    def get_all_runbooks_metadata(self) -> List[Dict]:
        """
        Get metadata for all runbooks in the knowledge base.
        
        Returns:
            List of runbook metadata dictionaries
        """
        try:
            all_docs = self.collection.get(include=["metadatas"])
            return all_docs["metadatas"]
        except Exception as e:
            print(f"Error getting runbooks metadata: {e}")
            return []

# Global instance
knowledge_base = None

def get_knowledge_base():
    """Get or create global knowledge base instance."""
    global knowledge_base
    if knowledge_base is None:
        knowledge_base = KnowledgeBase()
    return knowledge_base

def retrieve_runbooks(query: str, k: int = 3) -> str:
    """
    Retrieve relevant runbooks for a query using the knowledge base.
    
    Args:
        query: Query string to search for relevant runbooks
        k: Number of top results to return
        
    Returns:
        Formatted string of retrieved runbooks
    """
    kb = get_knowledge_base()
    return kb.retrieve_runbooks(query, k)

def create_knowledge_base(persist_directory: str = "./chroma_db") -> KnowledgeBase:
    """
    Create and initialize a new knowledge base.
    
    Args:
        persist_directory: Directory to store ChromaDB data
        
    Returns:
        Initialized KnowledgeBase instance
    """
    return KnowledgeBase(persist_directory)

# Example usage
if __name__ == "__main__":
    # Test the knowledge base
    kb = create_knowledge_base()
    
    # Test retrieval
    query = "Router CPU utilization going high"
    result = retrieve_runbooks(query, 2)
    print("Retrieved runbooks:")
    print(result)