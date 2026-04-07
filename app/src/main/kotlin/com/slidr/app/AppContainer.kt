package com.slidr.app

import android.content.Context
import com.slidr.app.data.repository.AuthRepository
import com.slidr.app.data.repository.MessageRepository
import com.slidr.app.data.repository.UserRepository

class AppContainer(context: Context) {
    val authRepository = AuthRepository(context)
    val userRepository = UserRepository()
    val messageRepository = MessageRepository()
}
