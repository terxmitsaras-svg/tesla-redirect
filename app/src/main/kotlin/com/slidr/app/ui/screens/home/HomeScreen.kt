package com.slidr.app.ui.screens.home

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.FilterList
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.RangeSlider
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import com.slidr.app.data.repository.MessageRepository
import com.slidr.app.data.repository.UserRepository
import com.slidr.app.ui.components.BottomNavBar
import com.slidr.app.ui.components.TagChip
import com.slidr.app.ui.components.UserGridCard
import com.slidr.app.ui.navigation.Screen
import com.slidr.app.ui.theme.Background
import com.slidr.app.ui.theme.Fuchsia
import com.slidr.app.ui.theme.Surface
import com.slidr.app.ui.theme.SurfaceVariant
import com.slidr.app.ui.theme.TextSecondary
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun HomeScreen(
    navController: NavController,
    userRepository: UserRepository,
    messageRepository: MessageRepository
) {
    val users by userRepository.nearbyUsers.collectAsState()
    val conversations by messageRepository.conversations.collectAsState()
    val unreadCount = conversations.sumOf { it.unreadCount }

    var showFilters by remember { mutableStateOf(false) }
    var onlineOnly by remember { mutableStateOf(false) }
    var ageRange by remember { mutableStateOf(18f..65f) }
    var distanceRange by remember { mutableFloatStateOf(10f) }
    val scope = rememberCoroutineScope()
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    val filteredUsers = users.filter { user ->
        (!onlineOnly || user.isOnline) &&
        user.age in ageRange.start.toInt()..ageRange.endInclusive.toInt() &&
        user.distanceKm <= distanceRange
    }

    Scaffold(
        containerColor = Background,
        topBar = {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Background)
                    .statusBarsPadding()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "slidr",
                    color = Fuchsia,
                    fontSize = 28.sp,
                    fontWeight = FontWeight.ExtraBold,
                    letterSpacing = (-1).sp
                )
                IconButton(onClick = { showFilters = true }) {
                    Icon(Icons.Filled.FilterList, contentDescription = "Filter", tint = Color.White)
                }
            }
        },
        bottomBar = {
            BottomNavBar(navController = navController, unreadCount = unreadCount)
        }
    ) { padding ->
        LazyVerticalGrid(
            columns = GridCells.Fixed(3),
            horizontalArrangement = Arrangement.spacedBy(2.dp),
            verticalArrangement = Arrangement.spacedBy(2.dp),
            modifier = Modifier
                .fillMaxSize()
                .background(Background)
                .padding(padding)
                .navigationBarsPadding()
        ) {
            items(filteredUsers, key = { it.id }) { user ->
                UserGridCard(
                    user = user,
                    onClick = {
                        navController.navigate(Screen.UserProfile.createRoute(user.id))
                    }
                )
            }
        }
    }

    if (showFilters) {
        ModalBottomSheet(
            onDismissRequest = { showFilters = false },
            sheetState = sheetState,
            containerColor = Surface
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 24.dp)
                    .padding(bottom = 32.dp)
            ) {
                Text("Filters", color = Color.White, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(24.dp))

                Text("Age range: ${ageRange.start.toInt()} – ${ageRange.endInclusive.toInt()}",
                    color = TextSecondary, fontSize = 14.sp)
                Spacer(Modifier.height(8.dp))
                RangeSlider(
                    value = ageRange,
                    onValueChange = { ageRange = it },
                    valueRange = 18f..65f,
                    colors = SliderDefaults.colors(
                        thumbColor = Fuchsia,
                        activeTrackColor = Fuchsia,
                        inactiveTrackColor = SurfaceVariant
                    )
                )

                Spacer(Modifier.height(16.dp))
                Text("Max distance: ${distanceRange.toInt()} km", color = TextSecondary, fontSize = 14.sp)
                Spacer(Modifier.height(8.dp))
                androidx.compose.material3.Slider(
                    value = distanceRange,
                    onValueChange = { distanceRange = it },
                    valueRange = 1f..50f,
                    colors = SliderDefaults.colors(
                        thumbColor = Fuchsia,
                        activeTrackColor = Fuchsia,
                        inactiveTrackColor = SurfaceVariant
                    )
                )

                Spacer(Modifier.height(16.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("Online only", color = Color.White, fontSize = 15.sp)
                    Switch(
                        checked = onlineOnly,
                        onCheckedChange = { onlineOnly = it },
                        colors = SwitchDefaults.colors(
                            checkedThumbColor = Color.White,
                            checkedTrackColor = Fuchsia
                        )
                    )
                }

                Spacer(Modifier.height(24.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Button(
                        onClick = {
                            ageRange = 18f..65f
                            distanceRange = 10f
                            onlineOnly = false
                        },
                        modifier = Modifier.weight(1f).height(48.dp),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = SurfaceVariant)
                    ) {
                        Text("Reset", color = TextSecondary)
                    }
                    Button(
                        onClick = { scope.launch { sheetState.hide(); showFilters = false } },
                        modifier = Modifier.weight(1f).height(48.dp),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Fuchsia)
                    ) {
                        Text("Apply", color = Color.White, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}
