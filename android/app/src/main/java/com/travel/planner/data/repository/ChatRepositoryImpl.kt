package com.travel.planner.data.repository

import com.travel.planner.data.remote.sse.SseClient
import com.travel.planner.data.remote.sse.SseEvent as SseSseEvent
import com.travel.planner.domain.repository.ChatRepository
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ChatRepositoryImpl @Inject constructor(
    private val sseClient: SseClient,
) : ChatRepository {

    override fun connectStream(sessionId: String, lastEventId: String?): Flow<SseSseEvent> =
        sseClient.connect(
            baseUrl = "",
            path = "chat/sessions/$sessionId/stream",
            lastEventId = lastEventId,
        )

    override fun cancelStream() = sseClient.cancel()

    override suspend fun createSession(title: String?): Result<String> {
        // Sessions are created via Retrofit POST, but SSE connects via OkHttp directly.
        // The POST is handled by the API layer; this is a placeholder.
        return Result.success("")
    }

    override suspend fun sendMessage(sessionId: String, content: String) {
        // Message sending is handled by the chat screen via Retrofit POST,
        // SSE connection is established separately via GET /stream.
    }

    override suspend fun getMessages(sessionId: String, page: Int): Result<List<com.travel.planner.domain.repository.Message>> {
        return Result.success(emptyList())
    }
}
