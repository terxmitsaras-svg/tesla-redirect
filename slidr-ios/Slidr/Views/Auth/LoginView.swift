import SwiftUI

struct LoginView: View {
    @EnvironmentObject var authRepo: AuthRepository
    @State private var email = ""
    @State private var password = ""
    @State private var showPassword = false
    @State private var errorMessage: String?
    @State private var isLoading = false
    @State private var showRegister = false

    var body: some View {
        NavigationStack {
            ZStack {
                Color.slidrBackground.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 0) {
                        Spacer().frame(height: 80)

                        // Logo
                        Text("slidr")
                            .font(.system(size: 56, weight: .black, design: .default))
                            .foregroundColor(.slidrFuchsia)
                            .tracking(-2)

                        Text("find your vibe")
                            .font(.system(size: 14, weight: .regular))
                            .foregroundColor(.slidrTextSecond)
                            .tracking(2)

                        Spacer().frame(height: 56)

                        // Email
                        SlidrTextField(text: $email, placeholder: "Email", keyboardType: .emailAddress)

                        Spacer().frame(height: 14)

                        // Password
                        SlidrSecureField(text: $password, placeholder: "Password", showText: $showPassword)

                        if let err = errorMessage {
                            Text(err)
                                .foregroundColor(.slidrError)
                                .font(.system(size: 13))
                                .multilineTextAlignment(.center)
                                .padding(.top, 8)
                        }

                        Spacer().frame(height: 28)

                        // Login button
                        Button {
                            isLoading = true
                            errorMessage = nil
                            let result = authRepo.login(email: email.trimmingCharacters(in: .whitespaces), password: password)
                            isLoading = false
                            if case .failure(let err) = result {
                                errorMessage = err.localizedDescription
                            }
                        } label: {
                            ZStack {
                                if isLoading {
                                    ProgressView().tint(.white)
                                } else {
                                    Text("Log In")
                                        .font(.system(size: 16, weight: .bold))
                                        .foregroundColor(.white)
                                }
                            }
                            .frame(maxWidth: .infinity)
                            .frame(height: 52)
                            .background(email.isEmpty || password.isEmpty ? Color.slidrFuchsia.opacity(0.4) : Color.slidrFuchsia)
                            .cornerRadius(12)
                        }
                        .disabled(email.isEmpty || password.isEmpty || isLoading)

                        Spacer().frame(height: 16)

                        Button("New here? Create account") {
                            showRegister = true
                        }
                        .foregroundColor(.slidrFuchsia)
                        .font(.system(size: 14))

                        Spacer().frame(height: 24)

                        Text("Demo: demo@slidr.app / demo123")
                            .foregroundColor(.slidrTextSecond.opacity(0.5))
                            .font(.system(size: 11))

                        Spacer().frame(height: 40)
                    }
                    .padding(.horizontal, 32)
                }
            }
            .navigationDestination(isPresented: $showRegister) {
                RegisterView()
            }
        }
    }
}

// MARK: - Helper input components
struct SlidrTextField: View {
    @Binding var text: String
    let placeholder: String
    var keyboardType: UIKeyboardType = .default

    var body: some View {
        TextField(placeholder, text: $text)
            .keyboardType(keyboardType)
            .autocorrectionDisabled()
            .textInputAutocapitalization(.never)
            .foregroundColor(.white)
            .padding()
            .background(Color.slidrSurface)
            .cornerRadius(12)
            .overlay(RoundedRectangle(cornerRadius: 12)
                .stroke(text.isEmpty ? Color.slidrTextSecond.opacity(0.3) : Color.slidrFuchsia, lineWidth: 1))
    }
}

struct SlidrSecureField: View {
    @Binding var text: String
    let placeholder: String
    @Binding var showText: Bool

    var body: some View {
        HStack {
            Group {
                if showText {
                    TextField(placeholder, text: $text)
                } else {
                    SecureField(placeholder, text: $text)
                }
            }
            .foregroundColor(.white)

            Button { showText.toggle() } label: {
                Image(systemName: showText ? "eye.slash" : "eye")
                    .foregroundColor(.slidrTextSecond)
            }
        }
        .padding()
        .background(Color.slidrSurface)
        .cornerRadius(12)
        .overlay(RoundedRectangle(cornerRadius: 12)
            .stroke(text.isEmpty ? Color.slidrTextSecond.opacity(0.3) : Color.slidrFuchsia, lineWidth: 1))
    }
}
