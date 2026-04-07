package com.slidr.app.data.repository

import com.slidr.app.data.mock.MockMessages
import com.slidr.app.data.model.Conversation
import com.slidr.app.data.model.Message
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import java.util.UUID

class MessageRepository {

    private val _messages = MutableStateFlow(MockMessages.MESSAGES.toMutableMap())

    private val _conversations = MutableStateFlow(buildConversations())
    val conversations: StateFlow<List<Conversation>> = _conversations.asStateFlow()

    private fun buildConversations(): List<Conversation> {
        return MockMessages.MESSAGES.map { (userId, messages) ->
            val last = messages.last()
            Conversation(
                userId = userId,
                lastMessage = last.text,
                lastMessageTime = last.timestamp,
                unreadCount = messages.count { !it.isRead && it.fromUserId != "me" }
            )
        }.sortedByDescending { it.lastMessageTime }
    }

    fun getMessages(userId: String): StateFlow<List<Message>> {
        val messages = _messages.value[userId] ?: emptyList()
        return MutableStateFlow(messages).asStateFlow()
    }

    fun sendMessage(toUserId: String, text: String) {
        val newMessage = Message(
            id = UUID.randomUUID().toString(),
            fromUserId = "me",
            toUserId = toUserId,
            text = text,
            timestamp = System.currentTimeMillis(),
            isRead = true
        )
        _messages.update { map ->
            val updated = map.toMutableMap()
            val list = (updated[toUserId] ?: emptyList()).toMutableList()
            list.add(newMessage)
            updated[toUserId] = list
            updated
        }
        refreshConversations()
    }

    fun markRead(userId: String) {
        _messages.update { map ->
            val updated = map.toMutableMap()
            val list = (updated[userId] ?: emptyList()).map { it.copy(isRead = true) }
            updated[userId] = list
            updated
        }
        refreshConversations()
    }

    fun getMessagesForUser(userId: String): List<Message> {
        return _messages.value[userId] ?: emptyList()
    }

    private fun refreshConversations() {
        _conversations.update {
            _messages.value.map { (userId, messages) ->
                val last = messages.last()
                Conversation(
                    userId = userId,
                    lastMessage = last.text,
                    lastMessageTime = last.timestamp,
                    unreadCount = messages.count { !it.isRead && it.fromUserId != "me" }
                )
            }.sortedByDescending { it.lastMessageTime }
        }
    }

    fun startConversation(userId: String) {
        _messages.update { map ->
            if (map.containsKey(userId)) map
            else {
                val updated = map.toMutableMap()
                updated[userId] = emptyList()
                updated
            }
        }
        refreshConversations()
    }

    val totalUnread: Int
        get() = _conversations.value.sumOf { it.unreadCount }
}
