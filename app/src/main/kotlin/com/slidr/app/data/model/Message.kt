package com.slidr.app.data.model

data class Message(
    val id: String,
    val fromUserId: String,
    val toUserId: String,
    val text: String,
    val timestamp: Long,
    val isRead: Boolean = false
)
