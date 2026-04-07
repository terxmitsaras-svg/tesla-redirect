import Foundation
import Combine

class UserRepository: ObservableObject {
    @Published var nearbyUsers: [User] = MockUsers.all
    @Published var currentUser: User = MockUsers.me

    func getUserById(_ id: String) -> User? {
        nearbyUsers.first { $0.id == id }
    }

    func toggleFavorite(userId: String) {
        if let idx = nearbyUsers.firstIndex(where: { $0.id == userId }) {
            nearbyUsers[idx].isFavorite.toggle()
        }
    }

    func updateCurrentUser(_ user: User) {
        currentUser = user
    }
}
