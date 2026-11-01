package com.travel.planner.presentation.screens.travelogue

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
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
import com.travel.planner.domain.model.SocialMaterial
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
fun MaterialListScreen(
    tripId: String,
    onNavigateBack: () -> Unit,
    viewModel: MaterialListViewModel = hiltViewModel(),
) {
    LaunchedEffect(tripId) { viewModel.load(tripId) }
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("社交素材") },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    Button(onClick = { viewModel.generate(tripId) }) {
                        Text("生成素材")
                    }
                },
            )
        },
    ) { padding ->
        when {
            uiState.isGenerating -> LoadingIndicator(Modifier.padding(padding))
            uiState.materials.isEmpty() -> {
                Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("暂无素材", style = MaterialTheme.typography.bodyLarge)
                        Spacer(Modifier.height(8.dp))
                        Button(onClick = { viewModel.generate(tripId) }) { Text("一键生成") }
                    }
                }
            }
            else -> {
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(padding),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp),
                ) {
                    items(uiState.materials) { material ->
                        MaterialCard(
                            material = material,
                            onFavorite = { viewModel.toggleFavorite(material.id, !material.isFavorite) },
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun MaterialCard(
    material: SocialMaterial,
    onFavorite: () -> Unit,
) {
    Card {
        Column(Modifier.padding(12.dp)) {
            // Header
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = when (material.type) {
                        "moment_9grid" -> "朋友圈9宫格"
                        "day_summary" -> "旅行卡片"
                        "trip_highlight" -> "精选合集"
                        "budget_card" -> "花费总结"
                        else -> material.type
                    },
                    style = MaterialTheme.typography.labelLarge,
                )
                IconButton(onClick = onFavorite) {
                    Icon(
                        if (material.isFavorite) Icons.Default.Favorite else Icons.Default.FavoriteBorder,
                        contentDescription = "Favorite",
                        tint = if (material.isFavorite) MaterialTheme.colorScheme.error
                            else MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            // Title/caption
            if (material.title != null) {
                Text(material.title, style = MaterialTheme.typography.bodyMedium)
            }

            // Photos
            if (material.images.isNotEmpty()) {
                Spacer(Modifier.height(8.dp))
                LazyRow(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    items(material.images) { img ->
                        AsyncImage(
                            model = img.url,
                            contentDescription = img.caption,
                            contentScale = ContentScale.Crop,
                            modifier = Modifier.size(100.dp),
                        )
                    }
                }
            }

            // Hashtags
            if (material.hashtags.isNotEmpty()) {
                Spacer(Modifier.height(4.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    material.hashtags.take(4).forEach { tag ->
                        Text(tag, style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.primary)
                    }
                }
            }
        }
    }
}

data class MaterialListUiState(
    val materials: List<SocialMaterial> = emptyList(),
    val isGenerating: Boolean = false,
)

@HiltViewModel
class MaterialListViewModel @Inject constructor(
    private val travelogueRepository: TravelogueRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(MaterialListUiState())
    val uiState: StateFlow<MaterialListUiState> = _uiState.asStateFlow()

    fun load(tripId: String) {
        viewModelScope.launch {
            travelogueRepository.listMaterials(tripId)
                .onSuccess { mats -> _uiState.value = MaterialListUiState(materials = mats) }
        }
    }

    fun generate(tripId: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isGenerating = true)
            travelogueRepository.generateMaterials(tripId)
                .onSuccess { mats -> _uiState.value = MaterialListUiState(materials = mats) }
                .onFailure { _uiState.value = _uiState.value.copy(isGenerating = false) }
        }
    }

    fun toggleFavorite(materialId: String, isFavorite: Boolean) {
        viewModelScope.launch {
            travelogueRepository.favoriteMaterial(materialId, isFavorite)
            val updated = _uiState.value.materials.map {
                if (it.id == materialId) it.copy(isFavorite = isFavorite) else it
            }
            _uiState.value = _uiState.value.copy(materials = updated)
        }
    }
}
