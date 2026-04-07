package com.slidr.app.ui.screens.profile

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
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
import com.slidr.app.data.repository.UserRepository
import com.slidr.app.ui.components.BottomNavBar
import com.slidr.app.ui.components.TagChip
import com.slidr.app.ui.navigation.Screen
import com.slidr.app.ui.theme.Background
import com.slidr.app.ui.theme.Divider
import com.slidr.app.ui.theme.Fuchsia
import com.slidr.app.ui.theme.SurfaceVariant
import com.slidr.app.ui.theme.TextSecondary

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun MyProfileScreen(
    navController: NavController,
    userRepository: UserRepository
) {
    val me by userRepository.currentUser.collectAsState()

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
                Text("My Profile", color = Color.White, fontSize = 22.sp, fontWeight = FontWeight.Bold)
                IconButton(onClick = { navController.navigate(Screen.Settings.route) }) {
                    Icon(Icons.Filled.Settings, contentDescription = "Settings", tint = Color.White)
                }
            }
        },
        bottomBar = { BottomNavBar(navController = navController) }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 20.dp)
        ) {
            item {
                Spacer(Modifier.height(20.dp))

                // Avatar + edit
                Box(contentAlignment = Alignment.BottomEnd) {
                    AsyncImage(
                        model = me.avatarUrl,
                        contentDescription = me.displayName,
                        contentScale = ContentScale.Crop,
                        modifier = Modifier
                            .size(100.dp)
                            .clip(CircleShape)
                    )
                    Box(
                        modifier = Modifier
                            .size(32.dp)
                            .clip(CircleShape)
                            .background(Fuchsia),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(Icons.Filled.Edit, contentDescription = "Edit",
                            tint = Color.White, modifier = Modifier.size(16.dp))
                    }
                }

                Spacer(Modifier.height(12.dp))

                Text("${me.displayName}, ${me.age}", color = Color.White,
                    fontSize = 22.sp, fontWeight = FontWeight.Bold)
                Text(me.pronouns, color = TextSecondary, fontSize = 13.sp)

                Spacer(Modifier.height(16.dp))
                HorizontalDivider(color = Divider)
                Spacer(Modifier.height(16.dp))

                Text("Bio", color = TextSecondary, fontSize = 12.sp,
                    fontWeight = FontWeight.Medium, letterSpacing = 1.sp)
                Spacer(Modifier.height(6.dp))
                Text(me.bio, color = Color.White, fontSize = 15.sp, lineHeight = 22.sp)

                Spacer(Modifier.height(20.dp))
                HorizontalDivider(color = Divider)
                Spacer(Modifier.height(16.dp))

                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                    StatItem("Height", me.height)
                    StatItem("Body", me.bodyType)
                }

                Spacer(Modifier.height(20.dp))
                HorizontalDivider(color = Divider)
                Spacer(Modifier.height(16.dp))

                Text("Looking for", color = TextSecondary, fontSize = 12.sp,
                    fontWeight = FontWeight.Medium, letterSpacing = 1.sp)
                Spacer(Modifier.height(8.dp))
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    me.lookingFor.forEach { TagChip(it, selected = true) }
                }

                if (me.tags.isNotEmpty()) {
                    Spacer(Modifier.height(20.dp))
                    Text("Tags", color = TextSecondary, fontSize = 12.sp,
                        fontWeight = FontWeight.Medium, letterSpacing = 1.sp)
                    Spacer(Modifier.height(8.dp))
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        me.tags.forEach { TagChip(it) }
                    }
                }

                Spacer(Modifier.height(32.dp))
            }
        }
    }
}
