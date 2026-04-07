import Foundation
import Combine

class AuthRepository: ObservableObject {
    @Published var isLoggedIn: Bool
    @Published var isProfileSetUp: Bool

    private let defaults = UserDefaults.standard

    init() {
        isLoggedIn = defaults.bool(forKey: "isLoggedIn")
        isProfileSetUp = defaults.bool(forKey: "isProfileSetUp")
    }

    func login(email: String, password: String) -> Result<Void, Error> {
        if email == "demo@slidr.app" && password == "demo123" {
            defaults.set(true, forKey: "isLoggedIn")
            isLoggedIn = true
            return .success(())
        }
        return .failure(NSError(domain: "auth", code: 401,
            userInfo: [NSLocalizedDescriptionKey: "Invalid email or password"]))
    }

    func register(email: String, password: String, displayName: String) {
        defaults.set(true, forKey: "isLoggedIn")
        isLoggedIn = true
    }

    func completeProfileSetup() {
        defaults.set(true, forKey: "isProfileSetUp")
        isProfileSetUp = true
    }

    func logout() {
        defaults.set(false, forKey: "isLoggedIn")
        defaults.set(false, forKey: "isProfileSetUp")
        isLoggedIn = false
        isProfileSetUp = false
    }
}
