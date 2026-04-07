import Foundation

struct MockUsers {

    static let me = User(
        id: "me",
        displayName: "Alex",
        age: 27,
        bio: "Just moved to the city. Love hiking, craft beer, and spontaneous adventures.",
        avatarURL: "https://i.pravatar.cc/300?img=33",
        distanceKm: 0,
        isOnline: true,
        height: "5'11\"",
        bodyType: "Athletic",
        pronouns: "He/Him",
        lookingFor: ["Chat", "Dates", "Right Now"],
        tags: ["Masc", "Vers", "420 friendly", "Dog dad"]
    )

    static let all: [User] = [
        User(id: "1", displayName: "Marcus", age: 28, bio: "Personal trainer by day, chef by night.", avatarURL: "https://i.pravatar.cc/300?img=11", distanceKm: 0.3, isOnline: true, height: "6'1\"", bodyType: "Muscular", pronouns: "He/Him", lookingFor: ["Chat", "Right Now"], tags: ["Top", "Masc", "Hung"]),
        User(id: "2", displayName: "Jordan", age: 24, bio: "Art student and occasional DJ.", avatarURL: "https://i.pravatar.cc/300?img=12", distanceKm: 0.7, isOnline: true, height: "5'9\"", bodyType: "Slim", pronouns: "They/Them", lookingFor: ["Chat", "Dates"], tags: ["Vers", "Queer", "Artsy"]),
        User(id: "3", displayName: "Kai", age: 31, bio: "Software engineer. Netflix and chill, literally.", avatarURL: "https://i.pravatar.cc/300?img=13", distanceKm: 1.1, isOnline: false, height: "5'10\"", bodyType: "Average", pronouns: "He/Him", lookingFor: ["Dates", "Right Now"], tags: ["Bottom", "Masc", "Geek"]),
        User(id: "4", displayName: "Devon", age: 26, bio: "Yoga instructor and amateur photographer.", avatarURL: "https://i.pravatar.cc/300?img=14", distanceKm: 1.4, isOnline: true, height: "6'0\"", bodyType: "Lean", pronouns: "He/Him", lookingFor: ["Chat", "Dates", "Right Now"], tags: ["Vers", "Outdoorsy", "Spiritual"]),
        User(id: "5", displayName: "Riley", age: 22, bio: "College senior. Here for a good time.", avatarURL: "https://i.pravatar.cc/300?img=15", distanceKm: 1.8, isOnline: true, height: "5'8\"", bodyType: "Slim", pronouns: "He/Him", lookingFor: ["Right Now"], tags: ["Bottom", "Twink", "Cat person"]),
        User(id: "6", displayName: "Zane", age: 34, bio: "Architect. I build beautiful things, including relationships.", avatarURL: "https://i.pravatar.cc/300?img=16", distanceKm: 2.0, isOnline: false, height: "6'2\"", bodyType: "Athletic", pronouns: "He/Him", lookingFor: ["Dates"], tags: ["Top", "Masc", "Beard"]),
        User(id: "7", displayName: "Theo", age: 29, bio: "Emergency room nurse. Need to decompress.", avatarURL: "https://i.pravatar.cc/300?img=17", distanceKm: 2.3, isOnline: true, height: "5'11\"", bodyType: "Lean", pronouns: "He/Him", lookingFor: ["Chat", "Dates", "Right Now"], tags: ["Vers", "Masc", "Night owl"]),
        User(id: "8", displayName: "Elliot", age: 25, bio: "Barista and aspiring novelist.", avatarURL: "https://i.pravatar.cc/300?img=18", distanceKm: 2.6, isOnline: false, height: "5'9\"", bodyType: "Slim", pronouns: "He/They", lookingFor: ["Chat", "Dates"], tags: ["Vers", "Bookworm", "Hipster"]),
        User(id: "9", displayName: "Nate", age: 32, bio: "Marine biologist. Great listener.", avatarURL: "https://i.pravatar.cc/300?img=19", distanceKm: 2.9, isOnline: true, height: "6'0\"", bodyType: "Average", pronouns: "He/Him", lookingFor: ["Dates", "Right Now"], tags: ["Bottom", "Outdoorsy", "Smart"]),
        User(id: "10", displayName: "Finn", age: 23, bio: "Music producer. Slide into my DMs like a bassline.", avatarURL: "https://i.pravatar.cc/300?img=20", distanceKm: 3.1, isOnline: true, height: "5'10\"", bodyType: "Athletic", pronouns: "He/Him", lookingFor: ["Chat", "Right Now"], tags: ["Vers", "Creative", "Night owl"]),
        User(id: "11", displayName: "Cole", age: 37, bio: "Dad of two. Looking for fun without complications.", avatarURL: "https://i.pravatar.cc/300?img=21", distanceKm: 3.4, isOnline: false, height: "6'1\"", bodyType: "Muscular", pronouns: "He/Him", lookingFor: ["Right Now"], tags: ["Top", "Masc", "Beard"]),
        User(id: "12", displayName: "Milo", age: 20, bio: "Just turned 20. Still figuring things out.", avatarURL: "https://i.pravatar.cc/300?img=22", distanceKm: 3.7, isOnline: true, height: "5'8\"", bodyType: "Slim", pronouns: "He/Him", lookingFor: ["Chat", "Dates"], tags: ["Bottom", "Twink", "Shy"]),
        User(id: "13", displayName: "Archer", age: 30, bio: "Former military, now running a startup.", avatarURL: "https://i.pravatar.cc/300?img=23", distanceKm: 3.9, isOnline: false, height: "6'3\"", bodyType: "Muscular", pronouns: "He/Him", lookingFor: ["Dates", "Right Now"], tags: ["Top", "Dominant", "Beard"]),
        User(id: "14", displayName: "Sage", age: 28, bio: "Therapist who needs therapy. Emotionally available.", avatarURL: "https://i.pravatar.cc/300?img=24", distanceKm: 4.1, isOnline: true, height: "5'10\"", bodyType: "Average", pronouns: "They/He", lookingFor: ["Chat", "Dates"], tags: ["Vers", "Queer", "Smart"]),
        User(id: "15", displayName: "Remy", age: 33, bio: "Chef at a Michelin-starred restaurant.", avatarURL: "https://i.pravatar.cc/300?img=25", distanceKm: 4.3, isOnline: false, height: "6'0\"", bodyType: "Athletic", pronouns: "He/Him", lookingFor: ["Dates", "Right Now"], tags: ["Vers", "Foodie", "Romantic"]),
        User(id: "16", displayName: "Jasper", age: 26, bio: "Graphic designer. Looking for my player 2.", avatarURL: "https://i.pravatar.cc/300?img=26", distanceKm: 4.5, isOnline: true, height: "5'9\"", bodyType: "Slim", pronouns: "He/Him", lookingFor: ["Dates"], tags: ["Bottom", "Geek", "Gamer"]),
        User(id: "17", displayName: "River", age: 21, bio: "Environmental science student. Save the earth.", avatarURL: "https://i.pravatar.cc/300?img=27", distanceKm: 4.7, isOnline: true, height: "5'11\"", bodyType: "Lean", pronouns: "He/They", lookingFor: ["Chat", "Dates", "Right Now"], tags: ["Vers", "Outdoorsy", "Vegan"]),
        User(id: "18", displayName: "Knox", age: 35, bio: "Divorce lawyer. I know what not to do.", avatarURL: "https://i.pravatar.cc/300?img=28", distanceKm: 4.9, isOnline: false, height: "6'2\"", bodyType: "Average", pronouns: "He/Him", lookingFor: ["Chat", "Dates"], tags: ["Top", "Masc", "Professional"]),
        User(id: "19", displayName: "Felix", age: 29, bio: "Tattooed barber with soft hands.", avatarURL: "https://i.pravatar.cc/300?img=29", distanceKm: 5.0, isOnline: true, height: "5'10\"", bodyType: "Athletic", pronouns: "He/Him", lookingFor: ["Chat", "Right Now"], tags: ["Vers", "Tatted", "Masc"]),
        User(id: "20", displayName: "Orion", age: 42, bio: "Professor of art history. I can make any subject interesting.", avatarURL: "https://i.pravatar.cc/300?img=30", distanceKm: 5.2, isOnline: false, height: "6'0\"", bodyType: "Average", pronouns: "He/Him", lookingFor: ["Dates"], tags: ["Vers", "Intellectual", "Cultured"])
    ]
}
