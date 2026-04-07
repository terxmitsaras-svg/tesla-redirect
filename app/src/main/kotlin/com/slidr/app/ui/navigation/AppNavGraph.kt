package com.slidr.app.ui.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import com.slidr.app.AppContainer
import com.slidr.app.ui.screens.auth.LoginScreen
import com.slidr.app.ui.screens.auth.RegisterScreen
import com.slidr.app.ui.screens.chat.ChatScreen
import com.slidr.app.ui.screens.home.HomeScreen
import com.slidr.app.ui.screens.inbox.InboxScreen
import com.slidr.app.ui.screens.profile.MyProfileScreen
import com.slidr.app.ui.screens.profile.UserProfileScreen
import com.slidr.app.ui.screens.settings.SettingsScreen
import com.slidr.app.ui.screens.setup.ProfileSetupScreen

@Composable
fun AppNavGraph(
    navController: NavHostController,
    startDestination: String,
    container: AppContainer
) {
    NavHost(navController = navController, startDestination = startDestination) {

        composable(Screen.Login.route) {
            LoginScreen(navController = navController, authRepository = container.authRepository)
        }

        composable(Screen.Register.route) {
            RegisterScreen(navController = navController, authRepository = container.authRepository)
        }

        composable(Screen.ProfileSetup.route) {
            ProfileSetupScreen(
                navController = navController,
                authRepository = container.authRepository,
                userRepository = container.userRepository
            )
        }

        composable(Screen.Home.route) {
            HomeScreen(
                navController = navController,
                userRepository = container.userRepository,
                messageRepository = container.messageRepository
            )
        }

        composable(
            route = Screen.UserProfile.route,
            arguments = listOf(navArgument("userId") { type = NavType.StringType })
        ) { backStack ->
            UserProfileScreen(
                userId = backStack.arguments?.getString("userId") ?: "",
                navController = navController,
                userRepository = container.userRepository,
                messageRepository = container.messageRepository
            )
        }

        composable(Screen.Inbox.route) {
            InboxScreen(
                navController = navController,
                messageRepository = container.messageRepository,
                userRepository = container.userRepository
            )
        }

        composable(
            route = Screen.Chat.route,
            arguments = listOf(navArgument("userId") { type = NavType.StringType })
        ) { backStack ->
            ChatScreen(
                userId = backStack.arguments?.getString("userId") ?: "",
                navController = navController,
                messageRepository = container.messageRepository,
                userRepository = container.userRepository
            )
        }

        composable(Screen.MyProfile.route) {
            MyProfileScreen(
                navController = navController,
                userRepository = container.userRepository
            )
        }

        composable(Screen.Settings.route) {
            SettingsScreen(
                navController = navController,
                authRepository = container.authRepository
            )
        }
    }
}
