package com.travel.planner.data.remote.sse

import com.travel.planner.data.local.datastore.TokenStore
import kotlinx.coroutines.*
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.*
import java.io.BufferedReader
import java.io.InputStreamReader
import javax.inject.Inject
import javax.inject.Singleton

data class SseEvent(
    val id: String? = null,
    val event: String = "message",
    val data: JsonObject? = null,
)

@Singleton
class SseClient @Inject constructor(
    private val okHttpClient: OkHttpClient,
    private val tokenStore: TokenStore,
) {
    private val json = Json { ignoreUnknownKeys = true }
    private var activeCall: Call? = null

    fun connect(baseUrl: String, path: String, lastEventId: String? = null): Flow<SseEvent> =
        callbackFlow {
            val token = runBlocking { tokenStore.getAccessToken() }
            val urlBuilder = HttpUrl.Builder()
                .scheme("http")
                .host("10.0.2.2")
                .port(8000)
                .addPathSegments("api/v1/$path")
                .addQueryParameter("token", token)

            lastEventId?.let { urlBuilder.addQueryParameter("lastEventId", it) }

            val request = Request.Builder()
                .url(urlBuilder.build())
                .header("Accept", "text/event-stream")
                .header("Cache-Control", "no-cache")
                .build()

            activeCall = okHttpClient.newCall(request)

            var currentEvent = ""
            var currentData = StringBuilder()

            try {
                val response = activeCall!!.execute()
                val reader = BufferedReader(InputStreamReader(response.body?.byteStream()))

                var line: String?
                while (reader.readLine().also { line = it } != null) {
                    val l = line ?: break

                    when {
                        l.startsWith("event: ") -> {
                            currentEvent = l.removePrefix("event: ").trim()
                        }
                        l.startsWith("data: ") -> {
                            currentData.append(l.removePrefix("data: "))
                        }
                        l.isEmpty() && currentData.isNotEmpty() -> {
                            val dataJson = try {
                                json.parseToJsonElement(currentData.toString()).jsonObject
                            } catch (e: Exception) {
                                null
                            }
                            trySend(SseEvent(event = currentEvent, data = dataJson))
                            currentEvent = "message"
                            currentData = StringBuilder()
                        }
                        l.startsWith(": ") -> {
                            // SSE comment / keepalive — ignore
                        }
                    }
                }
            } catch (e: Exception) {
                if (!isActive) return@callbackFlow
                close(e)
            } finally {
                close()
            }

            awaitClose {
                activeCall?.cancel()
                activeCall = null
            }
        }

    fun cancel() {
        activeCall?.cancel()
        activeCall = null
    }
}
