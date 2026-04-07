package com.slidr.app.data.repository

import com.slidr.app.data.mock.MockUsers
import com.slidr.app.data.model.User
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

class UserRepository {

    private val _users = MutableStateFlow(MockUsers.USERS)
    val nearbyUsers: StateFlow<List<User>> = _users.asStateFlow()

    private val _currentUser = MutableStateFlow(MockUsers.ME)
    val currentUser: StateFlow<User> = _currentUser.asStateFlow()

    fun getUserById(id: String): User? = _users.value.find { it.id == id }

    fun toggleFavorite(userId: String) {
        _users.update { list ->
            list.map { if (it.id == userId) it.copy(isFavorite = !it.isFavorite) else it }
        }
    }

    fun updateCurrentUser(user: User) {
        _currentUser.update { user }
    }
}
