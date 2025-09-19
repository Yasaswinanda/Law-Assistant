import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Layout } from '../components/Layout';

interface Message {
  id: number;
  client_id: number;
  lawyer_id: number;
  sender_id: number;
  message: string;
  created_at: string;
}

interface Conversation {
  id: number;
  email: string;
  role: string;
  location_name?: string;
  last_message: string;
  last_at: string;
  last_sender_id: number;
}

interface ChatMessage {
  type: 'me' | 'other' | 'ai';
  content: string;
  timestamp: string;
}

export const ChatPage: React.FC = () => {
  const { user, token } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [aiMessage, setAiMessage] = useState('');
  const [currentTab, setCurrentTab] = useState<'ai' | 'human'>('ai');
  const [isLoading, setIsLoading] = useState(false);
  const chatRef = useRef<HTMLDivElement>(null);

  const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5000';

  useEffect(() => {
    loadConversations();
    const urlParams = new URLSearchParams(window.location.search);
    const withUserId = urlParams.get('with_user_id');
    if (withUserId) {
      setSelectedConversation(parseInt(withUserId));
      setCurrentTab('human');
    }
  }, []);

  useEffect(() => {
    if (selectedConversation) {
      loadMessages(selectedConversation);
    }
  }, [selectedConversation]);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  const loadConversations = async () => {
    try {
      const response = await fetch(`${API_BASE}/messages/partners`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setConversations(data.partners);
      }
    } catch (error) {
      console.error('Error loading conversations:', error);
    }
  };

  const loadMessages = async (withUserId: number) => {
    try {
      const response = await fetch(`${API_BASE}/messages/thread?with_user_id=${withUserId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        const chatMessages: ChatMessage[] = data.messages.map((msg: Message) => ({
          type: msg.sender_id === user?.id ? 'me' : 'other',
          content: msg.message,
          timestamp: msg.created_at,
        }));
        setMessages(chatMessages);
      }
    } catch (error) {
      console.error('Error loading messages:', error);
    }
  };

  const sendMessage = async () => {
    if (!newMessage.trim() || !selectedConversation) return;

    const messageToSend = newMessage;
    setNewMessage('');

    // Add message optimistically
    const newChatMessage: ChatMessage = {
      type: 'me',
      content: messageToSend,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, newChatMessage]);

    try {
      await fetch(`${API_BASE}/messages/send`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          to_user_id: selectedConversation,
          message: messageToSend,
        }),
      });

      // Reload conversations to update last message
      loadConversations();
    } catch (error) {
      console.error('Error sending message:', error);
    }
  };

  const sendAiMessage = async () => {
    if (!aiMessage.trim()) return;

    const messageToSend = aiMessage;
    setAiMessage('');
    setIsLoading(true);

    // Add user message
    const userMessage: ChatMessage = {
      type: 'me',
      content: messageToSend,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: messageToSend,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const aiResponse: ChatMessage = {
          type: 'ai',
          content: data.answer || 'No response received',
          timestamp: new Date().toISOString(),
        };
        setMessages(prev => [...prev, aiResponse]);
      } else {
        const aiError: ChatMessage = {
          type: 'ai',
          content: 'Sorry, I encountered an error processing your request.',
          timestamp: new Date().toISOString(),
        };
        setMessages(prev => [...prev, aiError]);
      }
    } catch (error) {
      console.error('Error sending AI message:', error);
      const aiError: ChatMessage = {
        type: 'ai',
        content: 'Sorry, I encountered an error processing your request.',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, aiError]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent, callback: () => void) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      callback();
    }
  };

  return (
    <Layout currentPage="chat">
      <div className="layout">
        {/* Left: Conversations */}
        <aside className="card left">
          <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ margin: 0 }}>Conversations</h3>
            <a href="/dashboard" className="btn">New…</a>
          </div>
          <div className="divider"></div>
          <div className="convos">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                className={`convo ${selectedConversation === conv.id ? 'active' : ''}`}
                onClick={() => setSelectedConversation(conv.id)}
              >
                <div>
                  <div className="name">{conv.email}</div>
                  <div className="meta">{conv.last_message.substring(0, 50)}...</div>
                </div>
                <span className="badge">{conv.role}</span>
              </div>
            ))}
          </div>
          <div className="divider"></div>
          <div className="muted" style={{ fontSize: '12px' }}>
            People you've messaged. Updates automatically.
          </div>
        </aside>

        {/* Center: Chat */}
        <div className="card">
          <div className="tabs">
            <button
              className={`btn ${currentTab === 'ai' ? 'active' : ''}`}
              onClick={() => setCurrentTab('ai')}
            >
              AI Assistant
            </button>
            <button
              className={`btn ${currentTab === 'human' ? 'active' : ''}`}
              onClick={() => setCurrentTab('human')}
            >
              Human Chat
            </button>
          </div>

          <div className="chat" ref={chatRef}>
            {messages.map((msg, index) => (
              <div key={index} className={`bubble ${msg.type}`}>
                {msg.content}
              </div>
            ))}
            {isLoading && currentTab === 'ai' && (
              <div className="bubble ai">
                <em>AI is thinking...</em>
              </div>
            )}
          </div>

          <div className="toolbar">
            {currentTab === 'ai' ? (
              <>
                <input
                  type="text"
                  value={aiMessage}
                  onChange={(e) => setAiMessage(e.target.value)}
                  onKeyPress={(e) => handleKeyPress(e, sendAiMessage)}
                  placeholder="Ask the AI assistant..."
                  disabled={isLoading}
                />
                <button className="btn prime" onClick={sendAiMessage} disabled={isLoading || !aiMessage.trim()}>
                  Send
                </button>
              </>
            ) : (
              <>
                <input
                  type="text"
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyPress={(e) => handleKeyPress(e, sendMessage)}
                  placeholder={selectedConversation ? "Type a message..." : "Select a conversation to start chatting"}
                  disabled={!selectedConversation}
                />
                <button 
                  className="btn prime" 
                  onClick={sendMessage} 
                  disabled={!selectedConversation || !newMessage.trim()}
                >
                  Send
                </button>
              </>
            )}
          </div>
        </div>

        {/* Right: Info */}
        <aside className="card">
          <h3 style={{ margin: '0 0 6px 0' }}>Tips</h3>
          <div className="divider"></div>
          <div className="list">
            <div className="muted" style={{ fontSize: '14px' }}>
              <p><strong>AI Assistant:</strong> Upload documents, ask legal questions, get instant help.</p>
              <p><strong>Human Chat:</strong> Direct messaging with lawyers and clients.</p>
              <p><strong>Privacy:</strong> All conversations are encrypted and secure.</p>
            </div>
          </div>
        </aside>
      </div>
    </Layout>
  );
};