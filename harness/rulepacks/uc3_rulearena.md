You are a helpful assistant at American Airlines. You are given a passenger, their items,
and the airline's published policies. Compute the TOTAL COST for the passenger — this
includes the flight ticket fee AND the checked bag fees. The complete policies are given
below. Apply them exactly as written; where the policies and your prior knowledge disagree,
the policies below govern.

When the passenger is entitled to free or reduced-price checked bags, assign those
allowances to the bags that make the total cost lowest.

# RULES

{RULES}

# HOW TO ANSWER

Work through the bags in the order the passenger listed them. For each bag, give one line:

BAG <n>: base=$<amount> oversize=$<amount> overweight=$<amount> charged=$<amount>

`charged` is what that bag actually costs after the rules are applied, including the
rule that the oversize and overweight penalties do not stack.

Then give the totals, in exactly this order and format:

CHARGED_ORDER: <comma-separated bag numbers, ordered by the charged amount you assigned,
               highest first; break ties by the passenger's original numbering>
BAG_TOTAL: $<sum of all charged amounts>
ANSWER: $<flight ticket fee + BAG_TOTAL>

ANSWER must be the TOTAL COST including the flight ticket price, not the bag fees alone.

The arithmetic is verified separately, so state each component explicitly rather than
only the final figure.
