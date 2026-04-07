import SwiftUI

struct RootView: View {
    @EnvironmentObject var authRepo: AuthRepository

    var body: some View {
        Group {
            if !authRepo.isLoggedIn {
                LoginView()
            } else if !authRepo.isProfileSetUp {
                ProfileSetupView()
            } else {
                MainTabView()
            }
        }
        .animation(.easeInOut(duration: 0.3), value: authRepo.isLoggedIn)
        .animation(.easeInOut(duration: 0.3), value: authRepo.isProfileSetUp)
    }
}
