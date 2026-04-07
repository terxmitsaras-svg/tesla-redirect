package com.slidr.app.ui.screens.setup

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AddAPhoto
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import com.slidr.app.data.repository.AuthRepository
import com.slidr.app.data.repository.UserRepository
import com.slidr.app.ui.components.TagChip
import com.slidr.app.ui.navigation.Screen
import com.slidr.app.ui.theme.Background
import com.slidr.app.ui.theme.Fuchsia
import com.slidr.app.ui.theme.SurfaceVariant
import com.slidr.app.ui.theme.TextSecondary
import kotlinx.coroutines.launch

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun ProfileSetupScreen(
    navController: NavController,
    authRepository: AuthRepository,
    userRepository: UserRepository
) {
    var step by remember { mutableIntStateOf(0) }
    var bio by remember { mutableStateOf("") }
    val selectedLookingFor = remember { mutableStateListOf<String>() }
    val selectedTags = remember { mutableStateListOf<String>() }
    val scope = rememberCoroutineScope()

    val lookingForOptions = listOf("Chat", "Dates", "Right Now", "Relationship", "Networking")
    val tagOptions = listOf("Masc", "Femme", "Top", "Bottom", "Vers", "DDF", "420 friendly",
        "Tatted", "Beard", "Gym rat", "Outdoorsy", "Geek", "Night owl", "Dog dad", "Cat person")

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Background)
            .systemBarsPadding()
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(Modifier.height(16.dp))

            // Step indicator
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                repeat(3) { index ->
                    Box(
                        modifier = Modifier
                            .size(if (index == step) 24.dp else 8.dp, 8.dp)
                            .clip(RoundedCornerShape(4.dp))
                            .background(if (index == step) Fuchsia else SurfaceVariant)
                    )
                }
            }

            Spacer(Modifier.height(32.dp))

            when (step) {
                0 -> {
                    Text("Add your photo", color = Color.White, fontSize = 24.sp, fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(8.dp))
                    Text("Show people who you are", color = TextSecondary, fontSize = 14.sp)
                    Spacer(Modifier.height(40.dp))

                    Box(
                        modifier = Modifier
                            .size(140.dp)
                            .clip(CircleShape)
                            .background(SurfaceVariant)
                            .border(2.dp, Fuchsia, CircleShape),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(Icons.Filled.Person, contentDescription = null,
                                tint = TextSecondary, modifier = Modifier.size(48.dp))
                            Spacer(Modifier.height(4.dp))
                            Icon(Icons.Filled.AddAPhoto, contentDescription = null,
                                tint = Fuchsia, modifier = Modifier.size(24.dp))
                        }
                    }

                    Spacer(Modifier.height(16.dp))
                    Text("Tap to add photo", color = TextSecondary, fontSize = 13.sp)
                    Spacer(Modifier.height(8.dp))
                    Text("(Using your default avatar for now)", color = TextSecondary.copy(alpha = 0.5f), fontSize = 11.sp)
                }

                1 -> {
                    Text("About you", color = Color.White, fontSize = 24.sp, fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(8.dp))
                    Text("Tell people a bit about yourself", color = TextSecondary, fontSize = 14.sp)
                    Spacer(Modifier.height(32.dp))

                    OutlinedTextField(
                        value = bio,
                        onValueChange = { if (it.length <= 150) bio = it },
                        label = { Text("Bio") },
                        placeholder = { Text("What are you about?", color = TextSecondary) },
                        minLines = 4,
                        maxLines = 5,
                        modifier = Modifier.fillMaxWidth(),
                        colors = com.slidr.app.ui.screens.auth.slidrTextFieldColors(),
                        shape = RoundedCornerShape(12.dp),
                        supportingText = {
                            Text("${bio.length}/150", color = TextSecondary, fontSize = 11.sp)
                        }
                    )
                }

                2 -> {
                    Text("What are you looking for?", color = Color.White, fontSize = 22.sp,
                        fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(8.dp))
                    Text("Select all that apply", color = TextSecondary, fontSize = 14.sp)
                    Spacer(Modifier.height(24.dp))

                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        lookingForOptions.forEach { option ->
                            val selected = option in selectedLookingFor
                            TagChip(
                                text = option,
                                selected = selected,
                                onClick = {
                                    if (selected) selectedLookingFor.remove(option)
                                    else selectedLookingFor.add(option)
                                }
                            )
                        }
                    }

                    Spacer(Modifier.height(32.dp))
                    Text("Your vibe", color = Color.White, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
                    Spacer(Modifier.height(4.dp))
                    Text("Pick up to 5 tags", color = TextSecondary, fontSize = 13.sp)
                    Spacer(Modifier.height(12.dp))

                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        tagOptions.forEach { tag ->
                            val selected = tag in selectedTags
                            TagChip(
                                text = tag,
                                selected = selected,
                                onClick = {
                                    if (selected) selectedTags.remove(tag)
                                    else if (selectedTags.size < 5) selectedTags.add(tag)
                                }
                            )
                        }
                    }
                }
            }

            Spacer(Modifier.height(40.dp))

            Button(
                onClick = {
                    if (step < 2) {
                        step++
                    } else {
                        scope.launch {
                            authRepository.completeProfileSetup()
                            navController.navigate(Screen.Home.route) {
                                popUpTo(Screen.Login.route) { inclusive = true }
                            }
                        }
                    }
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Fuchsia)
            ) {
                Text(
                    if (step < 2) "Continue" else "Get Started",
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                    fontSize = 16.sp
                )
            }

            if (step > 0) {
                Spacer(Modifier.height(12.dp))
                Button(
                    onClick = { step-- },
                    modifier = Modifier.fillMaxWidth().height(48.dp),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color.Transparent)
                ) {
                    Text("Back", color = TextSecondary, fontSize = 14.sp)
                }
            }

            Spacer(Modifier.height(32.dp))
        }
    }
}
