package com.slidr.app.data.repository

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "slidr_prefs")

class AuthRepository(private val context: Context) {

    companion object {
        private val IS_LOGGED_IN = booleanPreferencesKey("is_logged_in")
        private val CURRENT_USER_ID = stringPreferencesKey("current_user_id")
        private val IS_PROFILE_SET_UP = booleanPreferencesKey("is_profile_set_up")

        private const val DEMO_EMAIL = "demo@slidr.app"
        private const val DEMO_PASSWORD = "demo123"
    }

    val isLoggedIn: Flow<Boolean> = context.dataStore.data
        .map { it[IS_LOGGED_IN] ?: false }

    val isProfileSetUp: Flow<Boolean> = context.dataStore.data
        .map { it[IS_PROFILE_SET_UP] ?: false }

    suspend fun login(email: String, password: String): Result<Unit> {
        return if (email == DEMO_EMAIL && password == DEMO_PASSWORD) {
            context.dataStore.edit { prefs ->
                prefs[IS_LOGGED_IN] = true
                prefs[CURRENT_USER_ID] = "me"
            }
            Result.success(Unit)
        } else {
            Result.failure(Exception("Invalid email or password"))
        }
    }

    suspend fun register(email: String, password: String, displayName: String): Result<Unit> {
        context.dataStore.edit { prefs ->
            prefs[IS_LOGGED_IN] = true
            prefs[CURRENT_USER_ID] = "me"
        }
        return Result.success(Unit)
    }

    suspend fun completeProfileSetup() {
        context.dataStore.edit { prefs ->
            prefs[IS_PROFILE_SET_UP] = true
        }
    }

    suspend fun logout() {
        context.dataStore.edit { prefs ->
            prefs[IS_LOGGED_IN] = false
            prefs[IS_PROFILE_SET_UP] = false
        }
    }
}
