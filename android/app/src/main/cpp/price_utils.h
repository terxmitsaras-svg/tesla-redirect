#pragma once
#include <string>
#include <vector>

namespace posokanei {

// Parse a human-readable price string → double.
// Handles: "2,49 €"  "1.99€"  "1.234,56"  "3,00 €/kg"  "Τιμή: 2,49"
// Returns -1.0 on failure.
double parsePrice(const std::string& text);

// Format a price for Greek display: 2.49 → "2,49 €"
std::string formatPrice(double price);

// Index of the minimum element; -1 if prices is empty.
int findCheapestIndex(const std::vector<double>& prices);

} // namespace posokanei
