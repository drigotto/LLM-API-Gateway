import re
import time
import json
from typing import List, Dict, Any, Optional

class MessageProcessor:
    """
    Class for processing and enhancing messages before sending them to LLMs.
    """
    
    def __init__(self, system_message: Optional[str] = None):
        """
        Initialize the message processor with an optional default system message.
        
        Args:
            system_message: Default system message to use if none is provided
        """
        self.default_system_message = system_message or "You are a helpful AI assistant."
        
    def process_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Process a list of messages to prepare them for the LLM API.
        
        This method:
        1. Ensures there's a system message
        2. Validates message format
        3. Adds timestamps
        4. Can be extended with more preprocessing logic
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            
        Returns:
            Processed list of message dictionaries
        """
        processed_messages = []
        
        # Check if system message exists
        has_system_message = any(msg.get('role') == 'system' for msg in messages)
        
        # Add default system message if none exists
        if not has_system_message:
            processed_messages.append({
                'role': 'system',
                'content': self.default_system_message
            })
        
        # Process each message
        for msg in messages:
            # Validate message format
            if 'role' not in msg or 'content' not in msg:
                raise ValueError(f"Invalid message format: {msg}")
            
            # Ensure role is valid
            if msg['role'] not in ['system', 'user', 'assistant']:
                raise ValueError(f"Invalid role '{msg['role']}'. Must be 'system', 'user', or 'assistant'")
            
            # Add processed message
            processed_msg = {
                'role': msg['role'],
                'content': msg['content'],
                'timestamp': int(time.time())  # Add timestamp
            }
            
            processed_messages.append(processed_msg)
            
        return processed_messages
    
    def enhance_system_message(self, messages: List[Dict[str, str]], enhancements: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Enhance the system message with additional instructions or context.
        
        Args:
            messages: List of message dictionaries
            enhancements: Dictionary of enhancements to add (e.g., {'tone': 'friendly', 'expertise': 'technical'})
            
        Returns:
            Messages with enhanced system message
        """
        # Find system message
        system_index = next((i for i, msg in enumerate(messages) if msg.get('role') == 'system'), None)
        
        if system_index is None:
            # No system message found, create one
            messages.insert(0, {
                'role': 'system',
                'content': self.default_system_message
            })
            system_index = 0
        
        # Enhance system message
        system_content = messages[system_index]['content']
        enhancement_text = "\n".join([f"{k}: {v}" for k, v in enhancements.items()])
        messages[system_index]['content'] = f"{system_content}\n\nAdditional context:\n{enhancement_text}"
        
        return messages
    
    def extract_citations(self, text: str) -> (str, List[Dict[str, Any]]):
        """
        Extract citations from text and return the text with citation markers and a list of citations.
        
        Args:
            text: Text to extract citations from
            
        Returns:
            Tuple of (processed_text, citations)
        """
        # Simple pattern for citation extraction - can be made more sophisticated
        citation_pattern = r'\[(.*?)\]\((.*?)\)'
        citations = []
        
        # Find all citations
        matches = re.findall(citation_pattern, text)
        
        # Process each citation
        for i, (label, url) in enumerate(matches):
            citation_id = i + 1
            citations.append({
                'id': citation_id,
                'label': label,
                'url': url
            })
            
            # Replace citation in text with citation marker
            text = text.replace(f"[{label}]({url})", f"[{citation_id}]")
        
        return text, citations