package com.travel.planner.data.local.datastore

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "auth_tokens")

@Singleton
class TokenStore @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    companion object {
        private val KEY_ACCESS_TOKEN = stringPreferencesKey("access_token")
        private val KEY_REFRESH_TOKEN = stringPreferencesKey("refresh_token")
    }

    val accessToken = context.dataStore.data.map { it[KEY_ACCESS_TOKEN] ?: "" }
    val refreshToken = context.dataStore.data.map { it[KEY_REFRESH_TOKEN] ?: "" }

    suspend fun saveTokens(access: String, refresh: String) {
        context.dataStore.edit {
            it[KEY_ACCESS_TOKEN] = access
            it[KEY_REFRESH_TOKEN] = refresh
        }
    }

    suspend fun getAccessToken(): String = context.dataStore.data.first()[KEY_ACCESS_TOKEN] ?: ""
    suspend fun getRefreshToken(): String = context.dataStore.data.first()[KEY_REFRESH_TOKEN] ?: ""

    suspend fun clear() {
        context.dataStore.edit { it.clear() }
    }
}
