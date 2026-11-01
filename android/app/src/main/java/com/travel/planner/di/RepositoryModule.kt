package com.travel.planner.di

import com.travel.planner.data.remote.api.*
import com.travel.planner.data.remote.sse.SseClient
import com.travel.planner.data.repository.*
import com.travel.planner.data.local.datastore.TokenStore
import com.travel.planner.domain.repository.*
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object RepositoryModule {

    @Provides @Singleton
    fun provideAuthRepository(
        authApi: AuthApi,
        tokenStore: TokenStore,
    ): AuthRepository = AuthRepositoryImpl(authApi, tokenStore)

    @Provides @Singleton
    fun providePlanRepository(
        planApi: PlanApi,
        tripApi: TripApi,
    ): PlanRepository = PlanRepositoryImpl(planApi, tripApi)

    @Provides @Singleton
    fun provideTripRepository(
        tripApi: TripApi,
    ): TripRepository = TripRepositoryImpl(tripApi)

    @Provides @Singleton
    fun provideChatRepository(
        sseClient: SseClient,
    ): ChatRepository = ChatRepositoryImpl(sseClient)

    @Provides @Singleton
    fun provideTravelogueRepository(
        travelogueApi: TravelogueApi,
    ): TravelogueRepository = TravelogueRepositoryImpl(travelogueApi)
}
