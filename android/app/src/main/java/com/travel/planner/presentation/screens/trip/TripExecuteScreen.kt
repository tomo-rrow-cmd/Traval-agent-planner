package com.travel.planner.presentation.screens.trip

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.travel.planner.domain.model.*
import com.travel.planner.domain.model.PaginatedData
import com.travel.planner.domain.repository.TripRepository
import com.travel.planner.presentation.components.common.LoadingIndicator
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TripExecuteScreen(
    tripId: String,
    onNavigateToCheckIn: () -> Unit,
    onNavigateToMaterials: () -> Unit,
    onNavigateBack: () -> Unit,
    viewModel: TripExecuteViewModel = hiltViewModel(),
) {
    LaunchedEffect(tripId) { viewModel.load(tripId) }
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("行程执行中") },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        },
    ) { padding ->
        when (val state = uiState) {
            is TripExecuteUiState.Loading -> LoadingIndicator(Modifier.padding(padding))
            is TripExecuteUiState.Success -> {
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(padding),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp),
                ) {
                    // Progress Ring
                    item {
                        Card {
                            Column(Modifier.padding(20.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                                Text(
                                    text = "${state.progress.progressPct.toInt()}%",
                                    style = MaterialTheme.typography.headlineLarge,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.primary,
                                )
                                Text("打卡 ${state.progress.checkedIn}/${state.progress.totalPois}")
                                Spacer(Modifier.height(4.dp))
                                LinearProgressIndicator(
                                    progress = { (state.progress.progressPct / 100).toFloat() },
                                    modifier = Modifier.fillMaxWidth(),
                                )
                                Spacer(Modifier.height(8.dp))
                                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                                    StatItem("Day", "${state.trip.currentDay}")
                                    StatItem("已花", "¥${state.progress.budgetSpent.toInt()}")
                                    StatItem("剩余", "¥${state.progress.budgetRemain.toInt()}")
                                }
                            }
                        }
                    }

                    // Check-in button
                    item {
                        Button(
                            onClick = onNavigateToCheckIn,
                            modifier = Modifier.fillMaxWidth().height(56.dp),
                        ) {
                            Icon(Icons.Default.Place, null)
                            Spacer(Modifier.width(8.dp))
                            Text("签到打卡", style = MaterialTheme.typography.titleMedium)
                        }
                    }

                    // Check-in log
                    if (state.checkins.isNotEmpty()) {
                        item { Text("签到记录", style = MaterialTheme.typography.titleMedium) }
                        items(state.checkins) { c ->
                            Card {
                                Row(Modifier.padding(12.dp)) {
                                    Icon(if (c.poiType == "attraction") Icons.Default.Place else Icons.Default.Restaurant, null)
                                    Spacer(Modifier.width(8.dp))
                                    Column {
                                        Text(c.poiName, style = MaterialTheme.typography.bodyMedium)
                                        if (c.note != null) Text(c.note, style = MaterialTheme.typography.bodySmall)
                                    }
                                }
                            }
                        }
                    }

                    // Adjustments
                    if (state.adjustments.isNotEmpty()) {
                        item { Text("调整建议", style = MaterialTheme.typography.titleMedium,
                            color = MaterialTheme.colorScheme.error) }
                        items(state.adjustments) { adj ->
                            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) {
                                Column(Modifier.padding(12.dp)) {
                                    Text(adj.triggerType, fontWeight = FontWeight.Bold)
                                    Text(adj.reason ?: "")
                                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                        Button(onClick = { viewModel.acceptAdjustment(adj.id) }) { Text("接受") }
                                        OutlinedButton(onClick = { viewModel.rejectAdjustment(adj.id) }) { Text("忽略") }
                                    }
                                }
                            }
                        }
                    }

                    // Status controls
                    item {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedButton(
                                onClick = { viewModel.updateStatus("paused") },
                                modifier = Modifier.weight(1f),
                            ) { Text("暂停") }
                            OutlinedButton(
                                onClick = { viewModel.updateStatus("completed") },
                                modifier = Modifier.weight(1f),
                            ) { Text("完成旅行") }
                        }
                        Spacer(Modifier.height(8.dp))
                        OutlinedButton(
                            onClick = onNavigateToMaterials,
                            modifier = Modifier.fillMaxWidth(),
                        ) { Text("生成社交素材") }
                    }
                }
            }
            is TripExecuteUiState.Error -> {
                Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                    Text(state.message, color = MaterialTheme.colorScheme.error)
                }
            }
        }
    }
}

@Composable
private fun StatItem(label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        Text(label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

// ---- ViewModel ----

sealed class TripExecuteUiState {
    data object Loading : TripExecuteUiState()
    data class Success(
        val trip: Trip,
        val progress: TripProgress,
        val checkins: List<Checkin>,
        val adjustments: List<Adjustment>,
    ) : TripExecuteUiState()
    data class Error(val message: String) : TripExecuteUiState()
}

@HiltViewModel
class TripExecuteViewModel @Inject constructor(
    private val tripRepository: TripRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow<TripExecuteUiState>(TripExecuteUiState.Loading)
    val uiState: StateFlow<TripExecuteUiState> = _uiState.asStateFlow()
    private var tripId: String = ""

    fun load(id: String) {
        tripId = id
        viewModelScope.launch {
            try {
                val trip = tripRepository.getTrip(id).getOrThrow()
                val progress = tripRepository.getProgress(id).getOrThrow()
                val checkins = tripRepository.listCheckins(id).getOrDefault(PaginatedData()).list
                val adjustments = tripRepository.listAdjustments(id).getOrDefault(PaginatedData()).list
                _uiState.value = TripExecuteUiState.Success(trip, progress, checkins, adjustments)
            } catch (e: Exception) {
                _uiState.value = TripExecuteUiState.Error(e.message ?: "加载失败")
            }
        }
    }

    fun updateStatus(status: String) {
        viewModelScope.launch {
            tripRepository.updateStatus(tripId, status)
            load(tripId)
        }
    }

    fun acceptAdjustment(adjId: String) {
        viewModelScope.launch {
            tripRepository.acceptAdjustment(tripId, adjId)
            load(tripId)
        }
    }

    fun rejectAdjustment(adjId: String) {
        viewModelScope.launch {
            tripRepository.rejectAdjustment(tripId, adjId)
            load(tripId)
        }
    }
}
