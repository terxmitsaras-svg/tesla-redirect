package com.slidr.app.ui.screens.inbox

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Badge
import androidx.compose.material3.HorizontalDivider
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
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import coil.compose.AsyncImage
import com.slidr.app.data.model.Conversation
import com.slidr.app.data.repository.MessageRepository
import com.slidr.app.data.repository.UserRepository
import com.slidr.app.ui.components.BottomNavBar
import com.slidr.app.ui.navigation.Screen
import com.slidr.app.ui.theme.Background
import com.slidr.app.ui.theme.Divider
import com.slidr.app.ui.theme.Fuchsia
import com.slidr.app.ui.theme.Surface
import com.slidr.app.ui.theme.TextSecondary
import java.util.concurrent.TimeUnit

@Composable
fun InboxScreen(
    navController: NavController,
    messageRepository: MessageRepository,
    userRepository: UserRepository
) {
    val conversations by messageRepository.conversations.collectAsState()
    val unreadTotal = conversations.sumOf { it.unreadCount }

    Scaffold(
        containerColor = Background,
        topBar = {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Background)
                    .statusBarsPadding()
                    .padding(horizontal = 20.dp, vertical = 12.dp)
            ) {
                Text(
                    "Messages",
                    color = Color.White,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        },
        bottomBar = {
            BottomNavBar(navController = navController, unreadCount = unreadTotal)
        }
    ) { padding ->
        if (conversations.isEmpty()) {
            Box(
                modifier = Modifier.fillMaxSize().padding(padding),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("No messages yet", color = TextSecondary, fontSize = 16.sp)
                    Spacer(Modifier.height(8.dp))
                    Text("Start sliding into someone's DMs", color = TextSecondary.copy(alpha = 0.6f), fontSize = 13.sp)
                }
            }
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
            ) {
                items(conversations, key = { it.userId }) { conversation ->
                    val user = userRepository.getUserById(conversation.userId)
                    if (user != null) {
                        ConversationRow(
                            conversation = conversation,
                            avatarUrl = user.avatarUrl,
                            displayName = user.displayName,
                            isOnline = user.isOnline,
                            onClick = {
                                messageRepository.markRead(conversation.userId)
                                navController.navigate(Screen.Chat.createRoute(conversation.userId))
                            }
                        )
                        HorizontalDivider(
                            color = Divider,
                            modifier = Modifier.padding(start = 76.dp)
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ConversationRow(
    conversation: Conversation,
    avatarUrl: String,
    displayName: String,
    isOnline: Boolean,
    onClick: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .background(if (conversation.unreadCount > 0) Surface else Background)
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Avatar with online dot
        Box {
            AsyncImage(
                model = avatarUrl,
                contentDescription = displayName,
                contentScale = ContentScale.Crop,
                modifier = Modifier
                    .size(52.dp)
                    .clip(CircleShape)
            )
            if (conversation.unreadCount > 0) {
                Badge(
                    containerColor = Fuchsia,
                    modifier = Modifier.align(Alignment.TopEnd)
                ) {
                    Text(
                        conversation.unreadCount.toString(),
                        color = Color.White,
                        fontSize = 10.sp
                    )
                }
            }
        }

        Spacer(Modifier.width(12.dp))

        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = displayName,
                color = Color.White,
                fontWeight = if (conversation.unreadCount > 0) FontWeight.Bold else FontWeight.Normal,
                fontSize = 15.sp
            )
            Spacer(Modifier.height(2.dp))
            Text(
                text = conversation.lastMessage,
                color = if (conversation.unreadCount > 0) Color.White.copy(alpha = 0.85f) else TextSecondary,
                fontSize = 13.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                fontWeight = if (conversation.unreadCount > 0) FontWeight.Medium else FontWeight.Normal
            )
        }

        Spacer(Modifier.width(8.dp))

        Text(
            text = formatTime(conversation.lastMessageTime),
            color = if (conversation.unreadCount > 0) Fuchsia else TextSecondary,
            fontSize = 12.sp
        )
    }
}

private fun formatTime(timestamp: Long): String {
    val diff = System.currentTimeMillis() - timestamp
    return when {
        diff < TimeUnit.MINUTES.toMillis(1) -> "now"
        diff < TimeUnit.HOURS.toMillis(1) -> "${TimeUnit.MILLISECONDS.toMinutes(diff)}m"
        diff < TimeUnit.DAYS.toMillis(1) -> "${TimeUnit.MILLISECONDS.toHours(diff)}h"
        else -> "${TimeUnit.MILLISECONDS.toDays(diff)}d"
    }
}
