package com.travel.planner.presentation.screens.travelogue

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import coil.compose.AsyncImage
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.travel.planner.domain.model.Travelogue
import com.travel.planner.domain.repository.TravelogueRepository
import com.travel.planner.presentation.components.common.LoadingIndicator
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TravelogueScreen(
    travelogueId: String = "",
    shareCode: String = "",
    onNavigateBack: () -> Unit,
    viewModel: TravelogueViewModel = hiltViewModel(),
) {
    LaunchedEffect(travelogueId, shareCode) {
        when {
            travelogueId.isNotEmpty() -> viewModel.load(travelogueId)
            shareCode.isNotEmpty() -> viewModel.loadByShareCode(shareCode)
        }
    }
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(uiState.travelogue?.title ?: "游记") },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(onClick = { viewModel.share() }) {
                        Icon(Icons.Default.Share, contentDescription = "Share")
                    }
                },
            )
        },
    ) { padding ->
        val state = uiState
        when {
            state.isLoading -> LoadingIndicator(Modifier.padding(padding))
            state.travelogue != null -> {
                val t = state.travelogue
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(padding),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    // Cover image
                    if (t.coverUrl != null) {
                        item {
                            AsyncImage(
                                model = t.coverUrl,
                                contentDescription = null,
                                contentScale = ContentScale.Crop,
                                modifier = Modifier.fillMaxWidth().height(200.dp),
                            )
                        }
                    }

                    // Meta
                    item {
                        Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                            Text("${t.totalDays ?: 0}天")
                            Text("${t.totalPois ?: 0}个打卡点")
                            Text("¥${(t.totalCost ?: 0.0).toInt()}")
                        }
                    }

                    // Content (simple markdown rendering)
                    item {
                        Text(
                            text = t.content ?: "",
                            style = MaterialTheme.typography.bodyLarge,
                        )
                    }
                }
            }
        }
    }
}

data class TravelogueUiState(
    val isLoading: Boolean = true,
    val travelogue: Travelogue? = null,
)

@HiltViewModel
class TravelogueViewModel @Inject constructor(
    private val travelogueRepository: TravelogueRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(TravelogueUiState())
    val uiState: StateFlow<TravelogueUiState> = _uiState.asStateFlow()

    fun load(id: String) {
        viewModelScope.launch {
            travelogueRepository.getTravelogue(id)
                .onSuccess { t -> _uiState.value = TravelogueUiState(isLoading = false, travelogue = t) }
                .onFailure { _uiState.value = TravelogueUiState(isLoading = false) }
        }
    }

    fun loadByShareCode(code: String) {
        viewModelScope.launch {
            travelogueRepository.getShareByCode(code)
                .onSuccess { _uiState.value = TravelogueUiState(isLoading = false) }
        }
    }

    fun share() {
        viewModelScope.launch {
            val t = _uiState.value.travelogue ?: return@launch
            travelogueRepository.createShare("travelogue", t.id, null, null)
        }
    }
}
