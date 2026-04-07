package com.slidr.app.data.model

data class User(
    val id: String,
    val displayName: String,
    val age: Int,
    val bio: String,
    val avatarUrl: String,
    val distanceKm: Float,
    val isOnline: Boolean,
    val height: String,
    val bodyType: String,
    val pronouns: String,
    val lookingFor: List<String>,
    val tags: List<String>,
    val isFavorite: Boolean = false
)
