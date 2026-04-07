import SwiftUI

struct ProfileSetupView: View {
    @EnvironmentObject var authRepo: AuthRepository
    @State private var step = 0
    @State private var bio = ""
    @State private var selectedLookingFor: Set<String> = []
    @State private var selectedTags: Set<String> = []

    let lookingForOptions = ["Chat", "Dates", "Right Now", "Relationship", "Networking"]
    let tagOptions = ["Masc", "Femme", "Top", "Bottom", "Vers", "DDF", "420 friendly",
                      "Tatted", "Beard", "Gym rat", "Outdoorsy", "Geek", "Night owl", "Dog dad", "Cat person"]

    var body: some View {
        ZStack {
            Color.slidrBackground.ignoresSafeArea()

            VStack(spacing: 0) {
                // Step dots
                HStack(spacing: 8) {
                    ForEach(0..<3) { i in
                        Capsule()
                            .fill(i == step ? Color.slidrFuchsia : Color.slidrSurfaceVar)
                            .frame(width: i == step ? 24 : 8, height: 8)
                            .animation(.spring(), value: step)
                    }
                }
                .padding(.top, 60)

                ScrollView {
                    VStack(alignment: .leading, spacing: 0) {
                        Spacer().frame(height: 32)

                        switch step {
                        case 0: photoStep
                        case 1: bioStep
                        default: lookingForStep
                        }

                        Spacer().frame(height: 40)

                        // Buttons
                        Button {
                            if step < 2 { step += 1 }
                            else { authRepo.completeProfileSetup() }
                        } label: {
                            Text(step < 2 ? "Continue" : "Get Started")
                                .font(.system(size: 16, weight: .bold))
                                .foregroundColor(.white)
                                .frame(maxWidth: .infinity)
                                .frame(height: 52)
                                .background(Color.slidrFuchsia)
                                .cornerRadius(12)
                        }

                        if step > 0 {
                            Button { step -= 1 } label: {
                                Text("Back")
                                    .foregroundColor(.slidrTextSecond)
                                    .frame(maxWidth: .infinity)
                                    .frame(height: 48)
                            }
                        }

                        Spacer().frame(height: 40)
                    }
                    .padding(.horizontal, 24)
                }
            }
        }
    }

    var photoStep: some View {
        VStack(alignment: .center, spacing: 16) {
            Text("Add your photo").font(.system(size: 24, weight: .bold)).foregroundColor(.white)
            Text("Show people who you are").font(.system(size: 14)).foregroundColor(.slidrTextSecond)

            Spacer().frame(height: 24)

            ZStack(alignment: .bottomTrailing) {
                Circle()
                    .fill(Color.slidrSurfaceVar)
                    .frame(width: 140, height: 140)
                    .overlay(Circle().stroke(Color.slidrFuchsia, lineWidth: 2))
                    .overlay(
                        VStack {
                            Image(systemName: "person.fill")
                                .font(.system(size: 48))
                                .foregroundColor(.slidrTextSecond)
                        }
                    )
                Circle()
                    .fill(Color.slidrFuchsia)
                    .frame(width: 36, height: 36)
                    .overlay(Image(systemName: "camera.fill").font(.system(size: 14)).foregroundColor(.white))
            }

            Text("Tap to add photo").font(.system(size: 13)).foregroundColor(.slidrTextSecond)
            Text("(Using default avatar for now)").font(.system(size: 11)).foregroundColor(.slidrTextSecond.opacity(0.5))
        }
        .frame(maxWidth: .infinity)
    }

    var bioStep: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("About you").font(.system(size: 24, weight: .bold)).foregroundColor(.white)
            Text("Tell people a bit about yourself").font(.system(size: 14)).foregroundColor(.slidrTextSecond)

            Spacer().frame(height: 16)

            VStack(alignment: .trailing) {
                TextEditor(text: $bio)
                    .frame(height: 120)
                    .padding(8)
                    .background(Color.slidrSurface)
                    .cornerRadius(12)
                    .overlay(RoundedRectangle(cornerRadius: 12)
                        .stroke(Color.slidrFuchsia.opacity(0.5), lineWidth: 1))
                    .foregroundColor(.white)
                    .scrollContentBackground(.hidden)
                    .onChange(of: bio) { _, new in if new.count > 150 { bio = String(new.prefix(150)) } }
                Text("\(bio.count)/150").font(.system(size: 11)).foregroundColor(.slidrTextSecond)
            }
        }
    }

    var lookingForStep: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("What are you looking for?").font(.system(size: 22, weight: .bold)).foregroundColor(.white)
            Text("Select all that apply").font(.system(size: 14)).foregroundColor(.slidrTextSecond)

            FlowLayout(spacing: 8) {
                ForEach(lookingForOptions, id: \.self) { opt in
                    TagChip(text: opt, selected: selectedLookingFor.contains(opt)) {
                        if selectedLookingFor.contains(opt) { selectedLookingFor.remove(opt) }
                        else { selectedLookingFor.insert(opt) }
                    }
                }
            }

            Spacer().frame(height: 20)
            Text("Your vibe").font(.system(size: 18, weight: .semibold)).foregroundColor(.white)
            Text("Pick up to 5 tags").font(.system(size: 13)).foregroundColor(.slidrTextSecond)

            FlowLayout(spacing: 8) {
                ForEach(tagOptions, id: \.self) { tag in
                    TagChip(text: tag, selected: selectedTags.contains(tag)) {
                        if selectedTags.contains(tag) { selectedTags.remove(tag) }
                        else if selectedTags.count < 5 { selectedTags.insert(tag) }
                    }
                }
            }
        }
    }
}

// Simple flow layout
struct FlowLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = proposal.width ?? 0
        var height: CGFloat = 0
        var x: CGFloat = 0
        var rowH: CGFloat = 0

        for sub in subviews {
            let size = sub.sizeThatFits(.unspecified)
            if x + size.width > width && x > 0 {
                x = 0; height += rowH + spacing; rowH = 0
            }
            x += size.width + spacing
            rowH = max(rowH, size.height)
        }
        height += rowH
        return CGSize(width: width, height: height)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX
        var y = bounds.minY
        var rowH: CGFloat = 0

        for sub in subviews {
            let size = sub.sizeThatFits(.unspecified)
            if x + size.width > bounds.maxX && x > bounds.minX {
                x = bounds.minX; y += rowH + spacing; rowH = 0
            }
            sub.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(size))
            x += size.width + spacing
            rowH = max(rowH, size.height)
        }
    }
}
