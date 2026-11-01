package com.travel.planner.presentation.screens.plan

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Map
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
import com.travel.planner.domain.model.PaginatedData
import com.travel.planner.domain.model.PlanSummary
import com.travel.planner.domain.repository.PlanRepository
import com.travel.planner.presentation.components.common.LoadingIndicator
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PlanListScreen(
    onNavigateToPlan: (String) -> Unit,
    onNavigateBack: () -> Unit,
    viewModel: PlanListViewModel = hiltViewModel(),
) {
    LaunchedEffect(Unit) { viewModel.load() }
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("我的方案") },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        },
    ) { padding ->
        when (val state = uiState) {
            is PlanListUiState.Loading -> LoadingIndicator(Modifier.padding(padding))
            is PlanListUiState.Success -> {
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(padding),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(state.plans) { plan ->
                        Card(modifier = Modifier.fillMaxWidth().clickable { onNavigateToPlan(plan.id) }) {
                            Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Default.Map, null)
                                Spacer(Modifier.width(12.dp))
                                Column(Modifier.weight(1f)) {
                                    Text(plan.title.ifEmpty { plan.destination }, style = MaterialTheme.typography.titleMedium)
                                    Text("${plan.days}天 · ¥${plan.estimatedCost.toInt()} · ${plan.status}", style = MaterialTheme.typography.bodySmall)
                                }
                            }
                        }
                    }
                }
            }
            is PlanListUiState.Error -> {
                Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                    Text(state.message, color = MaterialTheme.colorScheme.error)
                }
            }
        }
    }
}

sealed class PlanListUiState {
    data object Loading : PlanListUiState()
    data class Success(val plans: List<PlanSummary>) : PlanListUiState()
    data class Error(val message: String) : PlanListUiState()
}

@HiltViewModel
class PlanListViewModel @Inject constructor(
    private val planRepository: PlanRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow<PlanListUiState>(PlanListUiState.Loading)
    val uiState: StateFlow<PlanListUiState> = _uiState.asStateFlow()

    fun load() {
        viewModelScope.launch {
            planRepository.listPlans()
                .onSuccess { data -> _uiState.value = PlanListUiState.Success(data.list) }
                .onFailure { e -> _uiState.value = PlanListUiState.Error(e.message ?: "加载失败") }
        }
    }
}
