package com.travel.planner.presentation.screens.trip

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CameraAlt
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
import com.travel.planner.data.remote.dto.CheckinRequest
import com.travel.planner.domain.repository.TripRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CheckInScreen(
    tripId: String,
    onCheckInComplete: () -> Unit,
    viewModel: CheckInViewModel = hiltViewModel(),
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    LaunchedEffect(uiState) {
        if (uiState is CheckInUiState.Success) {
            onCheckInComplete()
        }
    }

    var poiName by remember { mutableStateOf("") }
    var poiType by remember { mutableStateOf("attraction") }
    var rating by remember { mutableStateOf(5) }
    var cost by remember { mutableStateOf("") }
    var note by remember { mutableStateOf("") }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("签到打卡") },
                navigationIcon = {
                    IconButton(onClick = onCheckInComplete) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            // Type selector
            Text("类型", style = MaterialTheme.typography.labelLarge)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilterChip(selected = poiType == "attraction", onClick = { poiType = "attraction" },
                    label = { Text("景点") })
                FilterChip(selected = poiType == "restaurant", onClick = { poiType = "restaurant" },
                    label = { Text("餐厅") })
                FilterChip(selected = poiType == "hotel", onClick = { poiType = "hotel" },
                    label = { Text("酒店") })
            }

            OutlinedTextField(
                value = poiName, onValueChange = { poiName = it },
                label = { Text("地点名称") },
                modifier = Modifier.fillMaxWidth(),
            )

            OutlinedTextField(
                value = cost, onValueChange = { cost = it },
                label = { Text("实际花费 ¥") },
                modifier = Modifier.fillMaxWidth(),
            )

            Text("评分", style = MaterialTheme.typography.labelLarge)
            Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                (1..5).forEach { i ->
                    IconButton(onClick = { rating = i }) {
                        Text(
                            "★",
                            style = MaterialTheme.typography.headlineMedium,
                            color = if (i <= rating) MaterialTheme.colorScheme.primary
                                else MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.15f),
                        )
                    }
                }
            }

            OutlinedTextField(
                value = note, onValueChange = { note = it },
                label = { Text("备注（记录此刻感受）") },
                modifier = Modifier.fillMaxWidth(),
                maxLines = 3,
            )

            OutlinedButton(
                onClick = { /* camera intent */ },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Icon(Icons.Default.CameraAlt, null)
                Spacer(Modifier.width(8.dp))
                Text("拍照")
            }

            Spacer(Modifier.weight(1f))

            Button(
                onClick = {
                    viewModel.checkin(
                        tripId,
                        CheckinRequest(
                            poiType = poiType,
                            poiName = poiName,
                            rating = rating,
                            actualCost = cost.toDoubleOrNull(),
                            note = note.ifBlank { null },
                        )
                    )
                },
                modifier = Modifier.fillMaxWidth().height(52.dp),
                enabled = poiName.isNotBlank() && uiState !is CheckInUiState.Loading,
            ) {
                if (uiState is CheckInUiState.Loading) {
                    CircularProgressIndicator(Modifier.size(24.dp))
                } else {
                    Text("确认签到 ✅")
                }
            }
        }
    }
}

sealed class CheckInUiState {
    data object Idle : CheckInUiState()
    data object Loading : CheckInUiState()
    data object Success : CheckInUiState()
}

@HiltViewModel
class CheckInViewModel @Inject constructor(
    private val tripRepository: TripRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow<CheckInUiState>(CheckInUiState.Idle)
    val uiState: StateFlow<CheckInUiState> = _uiState.asStateFlow()

    fun checkin(tripId: String, request: CheckinRequest) {
        viewModelScope.launch {
            _uiState.value = CheckInUiState.Loading
            tripRepository.checkin(tripId, request)
                .onSuccess { _uiState.value = CheckInUiState.Success }
                .onFailure { _uiState.value = CheckInUiState.Idle } // reset on error
        }
    }
}
