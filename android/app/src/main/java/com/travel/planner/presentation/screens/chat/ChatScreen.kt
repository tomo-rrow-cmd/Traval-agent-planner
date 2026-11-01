package com.travel.planner.presentation.screens.chat

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.travel.planner.data.remote.sse.SseClient
import com.travel.planner.domain.repository.ChatRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import kotlinx.serialization.json.jsonPrimitive
import javax.inject.Inject
import com.travel.planner.data.remote.sse.SseEvent

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    onNavigateToSession: (String) -> Unit,
    onNavigateBack: () -> Unit,
    viewModel: ChatListViewModel = hiltViewModel(),
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("AI 对话规划") },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Text(
                text = "告诉我你的旅行需求",
                style = MaterialTheme.typography.headlineMedium,
            )
            Spacer(Modifier.height(8.dp))
            Text(
                text = "例如：北京3天2人，喜欢历史人文，预算5000",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(24.dp))
            Button(
                onClick = {
                    viewModel.createSession { sessionId ->
                        onNavigateToSession(sessionId)
                    }
                },
                modifier = Modifier.fillMaxWidth().padding(horizontal = 48.dp).height(50.dp),
            ) {
                Text("开始规划")
            }
        }
    }
}

@HiltViewModel
class ChatListViewModel @Inject constructor() : ViewModel() {
    fun createSession(onCreated: (String) -> Unit) {
        val sessionId = java.util.UUID.randomUUID().toString()
        onCreated(sessionId)
    }
}

// ---- ChatSessionScreen ----

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatSessionScreen(
    sessionId: String,
    onPlanCreated: (String) -> Unit,
    onNavigateBack: () -> Unit,
    viewModel: ChatSessionViewModel = hiltViewModel(),
) {
    LaunchedEffect(sessionId) {
        viewModel.connect(sessionId)
    }

    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val listState = rememberLazyListState()
    var inputText by remember { mutableStateOf("") }

    // Auto-scroll when new messages arrive
    LaunchedEffect(uiState.messages.size) {
        if (uiState.messages.isNotEmpty()) {
            listState.animateScrollToItem(uiState.messages.size - 1)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("AI 规划中") },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        },
        bottomBar = {
            Surface(
                tonalElevation = 2.dp,
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    OutlinedTextField(
                        value = inputText,
                        onValueChange = { inputText = it },
                        placeholder = { Text("描述你的旅行需求...") },
                        modifier = Modifier.weight(1f),
                        singleLine = false,
                        maxLines = 3,
                    )
                    Spacer(Modifier.width(8.dp))
                    IconButton(
                        onClick = {
                            if (inputText.isNotBlank()) {
                                viewModel.sendMessage(inputText)
                                inputText = ""
                            }
                        },
                        enabled = inputText.isNotBlank() && !uiState.isStreaming,
                    ) {
                        Icon(Icons.Default.Send, contentDescription = "Send")
                    }
                }

                // Progress bar
                if (uiState.percent > 0 && uiState.percent < 100) {
                    LinearProgressIndicator(
                        progress = { uiState.percent / 100f },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Text(
                        text = uiState.progressLabel,
                        style = MaterialTheme.typography.labelSmall,
                        modifier = Modifier.padding(horizontal = 12.dp),
                    )
                }
            }
        },
    ) { padding ->
        LazyColumn(
            state = listState,
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            items(uiState.messages) { msg ->
                ChatBubble(
                    message = msg.content,
                    isUser = msg.role == "user",
                )
            }

            if (uiState.isStreaming) {
                item {
                    ChatBubble(
                        message = uiState.streamingText.ifEmpty { "思考中..." },
                        isUser = false,
                        isStreaming = true,
                    )
                }
            }

            // Show plan link when done
            val planId = uiState.planId
            if (planId != null) {
                item {
                    Button(
                        onClick = { onPlanCreated(planId) },
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Text("查看方案")
                    }
                }
            }
        }
    }
}

@Composable
fun ChatBubble(
    message: String,
    isUser: Boolean,
    isStreaming: Boolean = false,
) {
    Box(
        modifier = Modifier.fillMaxWidth(),
        contentAlignment = if (isUser) Alignment.CenterEnd else Alignment.CenterStart,
    ) {
        Surface(
            shape = MaterialTheme.shapes.medium,
            color = if (isUser) MaterialTheme.colorScheme.primaryContainer
                else MaterialTheme.colorScheme.surfaceVariant,
            modifier = Modifier.fillMaxWidth(0.85f),
        ) {
            Text(
                text = message,
                modifier = Modifier.padding(12.dp),
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}

// ---- ViewModel ----

data class ChatMessage(
    val role: String,
    val content: String,
)

data class ChatSessionUiState(
    val messages: List<ChatMessage> = emptyList(),
    val isStreaming: Boolean = false,
    val streamingText: String = "",
    val percent: Int = 0,
    val progressLabel: String = "",
    val planId: String? = null,
)

@HiltViewModel
class ChatSessionViewModel @Inject constructor(
    private val chatRepository: ChatRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(ChatSessionUiState())
    val uiState: StateFlow<ChatSessionUiState> = _uiState.asStateFlow()

    private var streamingJob: Job? = null

    fun connect(sessionId: String) {
        streamingJob?.cancel()
        streamingJob = viewModelScope.launch {
            chatRepository.connectStream(sessionId).collect { event ->
                handleSseEvent(event)
            }
        }
    }

    fun sendMessage(text: String) {
        val current = _uiState.value
        _uiState.value = current.copy(
            messages = current.messages + ChatMessage("user", text),
            isStreaming = true,
            streamingText = "",
        )
    }

    private fun handleSseEvent(event: SseEvent) {
        val current = _uiState.value

        when (event.event) {
            "message_delta" -> {
                val delta = event.data?.get("content_delta")?.jsonPrimitive?.content ?: ""
                _uiState.value = current.copy(streamingText = current.streamingText + delta)
            }
            "message" -> {
                val content = event.data?.get("content")?.jsonPrimitive?.content ?: ""
                _uiState.value = current.copy(
                    messages = current.messages + ChatMessage("assistant", content),
                    streamingText = "",
                )
            }
            "progress" -> {
                val percent = event.data?.get("percent")?.jsonPrimitive?.content?.toIntOrNull() ?: 0
                val label = event.data?.get("message")?.jsonPrimitive?.content ?: ""
                _uiState.value = current.copy(percent = percent, progressLabel = label)
            }
            "step_start" -> {
                val label = event.data?.get("label")?.jsonPrimitive?.content ?: ""
                _uiState.value = current.copy(progressLabel = label)
            }
            "done" -> {
                val planId = event.data?.get("plan_id")?.jsonPrimitive?.content
                _uiState.value = current.copy(
                    isStreaming = false,
                    percent = 100,
                    planId = planId,
                )
                streamingJob?.cancel()
            }
            "error" -> {
                _uiState.value = current.copy(isStreaming = false)
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        streamingJob?.cancel()
        chatRepository.cancelStream()
    }
}
