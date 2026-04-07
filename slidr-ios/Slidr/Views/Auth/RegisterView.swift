import SwiftUI

struct RegisterView: View {
    @EnvironmentObject var authRepo: AuthRepository
    @Environment(\.dismiss) var dismiss

    @State private var displayName = ""
    @State private var email = ""
    @State private var password = ""
    @State private var confirmPassword = ""
    @State private var showPassword = false
    @State private var errorMessage: String?

    var body: some View {
        ZStack {
            Color.slidrBackground.ignoresSafeArea()

            ScrollView {
                VStack(spacing: 0) {
                    Spacer().frame(height: 40)

                    Text("Create Account")
                        .font(.system(size: 28, weight: .bold))
                        .foregroundColor(.white)

                    Text("Join the community")
                        .font(.system(size: 14))
                        .foregroundColor(.slidrTextSecond)
                        .padding(.top, 4)

                    Spacer().frame(height: 36)

                    SlidrTextField(text: $displayName, placeholder: "Display Name")
                    Spacer().frame(height: 14)
                    SlidrTextField(text: $email, placeholder: "Email", keyboardType: .emailAddress)
                    Spacer().frame(height: 14)
                    SlidrSecureField(text: $password, placeholder: "Password", showText: $showPassword)
                    Spacer().frame(height: 14)
                    SlidrSecureField(text: $confirmPassword, placeholder: "Confirm Password", showText: $showPassword)

                    if let err = errorMessage {
                        Text(err).foregroundColor(.slidrError).font(.system(size: 13)).padding(.top, 8)
                    }

                    Spacer().frame(height: 28)

                    Button {
                        if displayName.isEmpty { errorMessage = "Enter a display name"; return }
                        if email.isEmpty { errorMessage = "Enter your email"; return }
                        if password.count < 6 { errorMessage = "Password must be at least 6 characters"; return }
                        if password != confirmPassword { errorMessage = "Passwords don't match"; return }
                        authRepo.register(email: email, password: password, displayName: displayName)
                    } label: {
                        Text("Create Account")
                            .font(.system(size: 16, weight: .bold))
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .frame(height: 52)
                            .background(Color.slidrFuchsia)
                            .cornerRadius(12)
                    }

                    Spacer().frame(height: 40)
                }
                .padding(.horizontal, 32)
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbarBackground(Color.slidrBackground, for: .navigationBar)
        .toolbarBackground(.visible, for: .navigationBar)
    }
}
