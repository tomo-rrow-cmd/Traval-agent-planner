package com.travel.planner.data.repository

import com.travel.planner.data.local.datastore.TokenStore
import com.travel.planner.data.remote.api.AuthApi
import com.travel.planner.data.remote.dto.LoginRequest
import com.travel.planner.data.remote.dto.RefreshTokenRequest
import com.travel.planner.data.remote.dto.RegisterRequest
import com.travel.planner.domain.model.TokenResult
import com.travel.planner.domain.repository.AuthRepository
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthRepositoryImpl @Inject constructor(
    private val authApi: AuthApi,
    private val tokenStore: TokenStore,
) : AuthRepository {

    override suspend fun login(phone: String, password: String): Result<TokenResult> = runCatching {
        val response = authApi.login(LoginRequest(phone = phone, password = password))
        val token = response.data ?: throw Exception(response.message)
        tokenStore.saveTokens(token.accessToken, token.refreshToken)
        token
    }

    override suspend fun loginWithSms(phone: String, code: String): Result<TokenResult> = runCatching {
        val response = authApi.login(LoginRequest(method = "phone", phone = phone, code = code))
        val token = response.data ?: throw Exception(response.message)
        tokenStore.saveTokens(token.accessToken, token.refreshToken)
        token
    }

    override suspend fun register(phone: String, password: String, nickname: String?): Result<TokenResult> = runCatching {
        val response = authApi.register(RegisterRequest(phone, password, nickname))
        val token = response.data ?: throw Exception(response.message)
        tokenStore.saveTokens(token.accessToken, token.refreshToken)
        token
    }

    override suspend fun refreshToken(refreshToken: String): Result<TokenResult> = runCatching {
        val response = authApi.refreshToken(RefreshTokenRequest(refreshToken))
        val token = response.data ?: throw Exception(response.message)
        tokenStore.saveTokens(token.accessToken, token.refreshToken)
        token
    }

    override suspend fun logout() {
        runCatching { authApi.logout() }
        tokenStore.clear()
    }

    override suspend fun isLoggedIn(): Boolean =
        tokenStore.getAccessToken().isNotEmpty()

    override fun getAccessToken(): Flow<String> = tokenStore.accessToken
}
