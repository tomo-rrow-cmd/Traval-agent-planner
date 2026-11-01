package com.travel.planner.data.remote.api

import com.travel.planner.data.remote.dto.*
import com.travel.planner.domain.model.ApiResponse
import com.travel.planner.domain.model.TokenResult
import com.travel.planner.domain.model.UserProfile
import retrofit2.http.*

interface AuthApi {

    @POST("auth/register")
    suspend fun register(@Body request: RegisterRequest): ApiResponse<TokenResult>

    @POST("auth/sms-codes")
    suspend fun sendSmsCode(@Body request: SmsCodeRequest): ApiResponse<SmsCodeResult>

    @POST("auth/sessions")
    suspend fun login(@Body request: LoginRequest): ApiResponse<TokenResult>

    @POST("auth/tokens")
    suspend fun refreshToken(@Body request: RefreshTokenRequest): ApiResponse<TokenResult>

    @DELETE("auth/sessions/current")
    suspend fun logout(): ApiResponse<Unit>
}

interface ProfileApi {

    @GET("user/profile")
    suspend fun getProfile(): ApiResponse<UserProfile>

    @PUT("user/profile")
    suspend fun updateProfile(@Body request: UpdateProfileRequest): ApiResponse<UserProfile>
}
