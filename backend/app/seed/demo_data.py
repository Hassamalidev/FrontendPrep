"""Source articles for the demo seed.

These exist so a fresh install is not an empty shell: `python -m app.seed --demo`
runs them through the real generation pipeline, which both fills the question
bank and demonstrates what the engine actually produces. They are ordinary
current-affairs prose, chosen to exercise the different fact kinds the extractor
looks for -- dates, quantities, roles and named actors.
"""

from __future__ import annotations

DEMO_ARTICLES: list[dict] = [
    {
        "title": "Pakistan Navy commissions PNS Hangor at Karachi",
        "category": "defence",
        "service": "navy",
        "source_name": "Inter-Services Public Relations",
        "body": """
Pakistan Navy commissioned PNS Hangor at Karachi on 25 June 2024, marking the delivery of the
first of eight Hangor-class submarines. The submarine was built under an agreement worth
5 billion dollars signed in 2015 between Pakistan and China. Admiral Naveed Ashraf is the Chief
of Naval Staff of Pakistan. The vessel can remain submerged for 30 days and carries a crew of
38 sailors. Four of the eight boats are being constructed at Karachi Shipyard and Engineering
Works under a transfer-of-technology arrangement. The Ministry of Defence said the programme
will create 2,500 jobs in the domestic shipbuilding sector. The Hangor class displaces
2,800 tonnes and has a range of 12,000 kilometres. Naval officials stated that the class will
replace the ageing Agosta 90B fleet by 2030. The programme is regarded as the largest defence
export deal in the history of the Chinese shipbuilding industry.
""",
    },
    {
        "title": "Pakistan Air Force inducts additional JF-17 Thunder Block III fighters",
        "category": "defence",
        "service": "air_force",
        "source_name": "Pakistan Aeronautical Complex",
        "body": """
Pakistan Air Force inducted a further squadron of JF-17 Thunder Block III fighters at Kamra in
March 2024. The aircraft is co-produced by Pakistan Aeronautical Complex and Chengdu Aircraft
Corporation, with 58 percent of the airframe manufactured domestically. The Block III variant
carries an active electronically scanned array radar with a detection range of 170 kilometres.
Air Chief Marshal Zaheer Ahmed Babar is the Chief of Air Staff of Pakistan. The fighter has a
maximum speed of Mach 1.6 and a combat radius of 1,350 kilometres. Pakistan Air Force operates
more than 150 JF-17 aircraft across seven squadrons. The programme began in 1999 and the first
aircraft entered service in 2007. Officials said the induction reduces dependence on imported
platforms and supports 12,000 skilled jobs at Kamra.
""",
    },
    {
        "title": "Pakistan Army completes Exercise Hammer Strike in Thal desert",
        "category": "defence",
        "service": "army",
        "source_name": "Inter-Services Public Relations",
        "body": """
Pakistan Army completed Exercise Hammer Strike in the Thal desert in December 2023, involving
more than 15,000 troops from two strike formations. The exercise validated new operational
concepts over 21 days across an area of 400 square kilometres. General Asim Munir is the Chief
of Army Staff of Pakistan. Armoured, mechanised infantry and aviation units took part alongside
40 helicopters and 300 armoured vehicles. The exercise tested integration of unmanned aerial
systems with artillery for the first time at formation level. Army officials said the drills
rehearsed responses under a nuclear overhang and in a degraded communications environment.
The Pakistan Military Academy at Kakul commissions approximately 2,000 officers each year into
such formations.
""",
    },
    {
        "title": "State Bank raises policy rate as inflation eases",
        "category": "current_affairs",
        "service": None,
        "source_name": "State Bank of Pakistan",
        "body": """
The State Bank of Pakistan announced a policy rate of 22 percent in July 2024, holding it steady
for a fourth consecutive meeting. Headline inflation fell to 12.6 percent in June 2024 from a
peak of 38 percent in May 2023. The Monetary Policy Committee said foreign exchange reserves
stood at 9 billion dollars, covering roughly two months of imports. The committee expects
average inflation of 11 percent for the current fiscal year. Pakistan concluded a 3 billion
dollar standby arrangement with the International Monetary Fund in April 2024. The current
account deficit narrowed to 0.7 billion dollars over eleven months. Remittances from overseas
Pakistanis reached 30 billion dollars during the year, an increase of 11 percent.
""",
    },
]
