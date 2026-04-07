package com.slidr.app.data.model

data class Conversation(
    val userId: String,
    val lastMessage: String,
    val lastMessageTime: Long,
    val unreadCount: Int
)
