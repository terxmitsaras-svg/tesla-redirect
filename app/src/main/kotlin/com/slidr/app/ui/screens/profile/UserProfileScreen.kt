package com.slidr.app.ui.screens.profile

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
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.WifiTethering
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import coil.compose.AsyncImage
import com.slidr.app.data.repository.MessageRepository
import com.slidr.app.data.repository.UserRepository
import com.slidr.app.ui.components.TagChip
import com.slidr.app.ui.navigation.Screen
import com.slidr.app.ui.theme.Background
import com.slidr.app.ui.theme.Divider
import com.slidr.app.ui.theme.Fuchsia
import com.slidr.app.ui.theme.OnlineGreen
import com.slidr.app.ui.theme.Surface
import com.slidr.app.ui.theme.SurfaceVariant
import com.slidr.app.ui.theme.TextSecondary

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun UserProfileScreen(
    userId: String,
    navController: NavController,
    userRepository: UserRepository,
    messageRepository: MessageRepository
) {
    val users by userRepository.nearbyUsers.collectAsState()
    val user = users.find { it.id == userId }

    if (user == null) {
        Box(Modifier.fillMaxSize().background(Background), contentAlignment = Alignment.Center) {
            Text("User not found", color = TextSecondary)
        }
        return
    }

    Box(modifier = Modifier.fillMaxSize().background(Background)) {
        LazyColumn(modifier = Modifier.fillMaxSize()) {
            item {
                // Hero photo
                Box(modifier = Modifier.fillMaxWidth().height(360.dp)) {
                    AsyncImage(
                        model = user.avatarUrl,
                        contentDescription = user.displayName,
                        contentScale = ContentScale.Crop,
                        modifier = Modifier.fillMaxSize()
                    )
                    // Gradient overlay at top for back button readability
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(120.dp)
                            .background(
                                androidx.compose.ui.graphics.Brush.verticalGradient(
                                    listOf(Color(0x88000000), Color.Transparent)
                                )
                            )
                    )
                }
            }

            item {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(Background)
                        .padding(20.dp)
                ) {
                    // Name, age, status
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.Top
                    ) {
                        Column {
                            Text(
                                text = "${user.displayName}, ${user.age}",
                                color = Color.White,
                                fontSize = 26.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(4.dp)
                            ) {
                                if (user.isOnline) {
                                    Icon(Icons.Filled.WifiTethering, contentDescription = null,
                                        tint = OnlineGreen, modifier = Modifier.size(14.dp))
                                    Text("Online now", color = OnlineGreen, fontSize = 13.sp)
                                } else {
                                    Icon(Icons.Filled.LocationOn, contentDescription = null,
                                        tint = TextSecondary, modifier = Modifier.size(14.dp))
                                    val dist = user.distanceKm
                                    Text(
                                        "${"%.1f".format(dist)} km away",
                                        color = TextSecondary, fontSize = 13.sp
                                    )
                                }
                            }
                        }
                        Text(
                            text = user.pronouns,
                            color = TextSecondary,
                            fontSize = 13.sp,
                            modifier = Modifier
                                .clip(RoundedCornerShape(6.dp))
                                .background(SurfaceVariant)
                                .padding(horizontal = 10.dp, vertical = 4.dp)
                        )
                    }

                    Spacer(Modifier.height(20.dp))
                    HorizontalDivider(color = Divider)
                    Spacer(Modifier.height(16.dp))

                    // Bio
                    Text(user.bio, color = Color.White.copy(alpha = 0.9f), fontSize = 15.sp, lineHeight = 22.sp)

                    Spacer(Modifier.height(20.dp))
                    HorizontalDivider(color = Divider)
                    Spacer(Modifier.height(16.dp))

                    // Stats row
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceEvenly
                    ) {
                        StatItem("Height", user.height)
                        StatItem("Body", user.bodyType)
                    }

                    Spacer(Modifier.height(20.dp))
                    HorizontalDivider(color = Divider)
                    Spacer(Modifier.height(16.dp))

                    // Looking for
                    Text("Looking for", color = TextSecondary, fontSize = 12.sp, fontWeight = FontWeight.Medium,
                        letterSpacing = 1.sp)
                    Spacer(Modifier.height(8.dp))
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        user.lookingFor.forEach { TagChip(it, selected = true) }
                    }

                    Spacer(Modifier.height(20.dp))

                    // Tags
                    if (user.tags.isNotEmpty()) {
                        Text("Vibe", color = TextSecondary, fontSize = 12.sp, fontWeight = FontWeight.Medium,
                            letterSpacing = 1.sp)
                        Spacer(Modifier.height(8.dp))
                        FlowRow(
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            verticalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            user.tags.forEach { TagChip(it) }
                        }
                        Spacer(Modifier.height(20.dp))
                    }

                    HorizontalDivider(color = Divider)
                    Spacer(Modifier.height(20.dp))

                    // Action buttons
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Button(
                            onClick = {
                                messageRepository.startConversation(userId)
                                navController.navigate(Screen.Chat.createRoute(userId))
                            },
                            modifier = Modifier.weight(1f).height(52.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Fuchsia)
                        ) {
                            Text("Message", color = Color.White, fontWeight = FontWeight.Bold)
                        }

                        OutlinedButton(
                            onClick = { userRepository.toggleFavorite(userId) },
                            modifier = Modifier.height(52.dp),
                            shape = RoundedCornerShape(12.dp),
                            border = androidx.compose.foundation.BorderStroke(1.dp, Fuchsia)
                        ) {
                            Icon(
                                imageVector = if (user.isFavorite) Icons.Filled.Favorite
                                              else Icons.Filled.FavoriteBorder,
                                contentDescription = "Favorite",
                                tint = Fuchsia,
                                modifier = Modifier.size(20.dp)
                            )
                            Spacer(Modifier.width(6.dp))
                            Text(
                                if (user.isFavorite) "Saved" else "Save",
                                color = Fuchsia
                            )
                        }
                    }

                    Spacer(Modifier.height(32.dp))
                }
            }
        }

        // Back button overlay
        IconButton(
            onClick = { navController.popBackStack() },
            modifier = Modifier
                .statusBarsPadding()
                .padding(8.dp)
                .size(40.dp)
                .clip(CircleShape)
                .background(Color(0x66000000))
        ) {
            Icon(Icons.Filled.ArrowBack, contentDescription = "Back", tint = Color.White)
        }
    }
}

@Composable
private fun StatItem(label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(label, color = TextSecondary, fontSize = 12.sp)
        Spacer(Modifier.height(2.dp))
        Text(value, color = Color.White, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
    }
}
