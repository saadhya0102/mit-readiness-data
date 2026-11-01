import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(r"C:\Users\hasto\Demo Projects")
INVENTORY = ROOT / "mit_worker_29_roster_inventory.json"
OUTPUT = ROOT / "mit_worker_29_underclass_athletics.jsonl"

NOISE_RE = re.compile(
    r"(?i)^(graduated from|attended |favorite sports memory|before mit:?$|personal:?$)"
)
SENSITIVE_RE = re.compile(
    r"(?i)\b(african american|hispanic|latinx affinity|"
    r"south asian heritage|asian student association|black student union|"
    r"fellowship of christian athletes|gsa club|gender.sexuality alliance|"
    r"mental health club|bible study|vestry)\b"
)

CATEGORY_PATTERNS = [
    (
        "research_science_fair",
        re.compile(
            r"(?i)\b(research|science fair|ISEF|JSHS|NYSSEF|WESEF|LISEF|"
            r"Regeneron|laborator(?:y|ies)|lab intern|research intern|research assistant|"
            r"science talent|symposium|scientific paper|co-authored paper|"
            r"published paper|paper accepted|PJAS)\b"
        ),
    ),
    (
        "robotics_engineering",
        re.compile(
            r"(?i)\b(robot|robotics|engineering club|technology student association|"
            r"architecture intern|design team|3d print|laser cutter|machine shop|"
            r"CAD|speedmodeling)\b"
        ),
    ),
    (
        "cs_projects_competitions",
        re.compile(
            r"(?i)\b(coding|computer science|cyber|hackathon|app challenge|USACO|"
            r"programming|software)\b"
        ),
    ),
    (
        "debate_speech",
        re.compile(
            r"(?i)\b(debate|speech team|speech and debate|model united nations|model un|"
            r"model congress|mock trial)\b"
        ),
    ),
    (
        "entrepreneurship",
        re.compile(
            r"(?i)\b(DECA|FBLA|business professionals|entrepreneur|business accelerator|"
            r"future executive|case study competition|stock pitch)\b"
        ),
    ),
    (
        "writing_media",
        re.compile(
            r"(?i)\b(newspaper|journalis|yearbook|literary (arts )?magazine|"
            r"student publication|writing contest|editor|news magazine)\b"
        ),
    ),
    (
        "arts_music",
        re.compile(
            r"(?i)\b(choir|chorus|band|orchestra|piano|violin|music|theat(?:er|re)|"
            r"drama|dance|photograph|visual art|marching band|saxophone|guitar)\b"
        ),
    ),
    (
        "academic_olympiad",
        re.compile(
            r"(?i)\b(olympiad|AIME|USAMO|USABO|USNCO|science bowl|mathletes|"
            r"math team|chemistry team|physics team|scholar bowl|quiz bowl|"
            r"academic decathlon|it's academic|math challenge|national history day|"
            r"future problem solving|national latin exam|national german exam|"
            r"urban planning national champion|USA\(J\)MO|USAPhO)\b"
        ),
    ),
    (
        "community_civic",
        re.compile(
            r"(?i)\b(volunteer|community service|service club|Eagle Scout|Girl Scout|"
            r"Boy Scout|scouting|Key Club|Best Buddies|food ?bank|charity|Habitat|"
            r"Red Cross|HOSA|climate ambassador|sustainability club|outreach club|"
            r"tutor|mentor|nonprofit|non-profit|youth board|affinity|health initiative)\b"
        ),
    ),
    (
        "student_government_leadership",
        re.compile(
            r"(?i)\b(student council|student government|student senate|class president|"
            r"class parliamentarian|class officer|honor council|principal.?s advisory|"
            r"grade level representative|house prefect)\b"
        ),
    ),
    (
        "employment_family",
        re.compile(r"(?i)\b(employee|employment|worked as|barista|lifeguard|paid intern)\b"),
    ),
]

SPORT_RE = re.compile(
    r"(?i)\b(varsity|letterwinner|all[- ]?(?:state|conference|league|county|region|"
    r"section|district|area|academic|american|metro|new[- ]england|SPC)|"
    r"state champion|conference champion|league champion|"
    r"sectional champion|team captain|team mvp|athlet\w*|"
    r"scholar.?athlete|recruit|UTR|"
    r"swim\w*|soccer|football|basketball|baseball|softball|lacrosse|tennis|volleyball|"
        r"libero|"
    r"water polo|fencing|squash|rowing|crew|track|cross country|field hockey|golf|"
    r"ski|wrestl\w*|diving|sailing|regatta|badminton|trap shooting|skeet shooting|"
    r"air rifle|3PAR|junior olympics|olympic development program|AAU|"
    r"pole vault|javelin|shot put|hurdle|"
    r"freestyle|butterfly|backstroke|breaststroke|relay|NISCA|USA Lacrosse|"
    r"USAPL|USRowing|sportsmanship award|defensive player|offensive player|"
    r"player of the year|most valuable player|student[- ]athlete|scholar[- ]athlete|"
    r"athletic association|athletic excellence|athlete leadership|"
    r"CIF|NEPSAC|ISL|WIAA|MSHSAA|NCAA|ECNL|OIA|Stotesbury|SHORR|home run)\b"
)

BROAD_SPORT_RE = re.compile(
    r"(?i)(\bchampions?(?:hip)?s?\b|\bchamps?\b|\bsemifinalist\b|\bfinalist\b|"
    r"\bfirst team\b|\bsecond team\b|\b1st team\b|\b2nd team\b|"
    r"\bcaptain\b|\bMVP\b|\bmost valuable player\b|\brookie of the year\b|"
    r"\bmost improved player\b|\ball-star\b|\ball-[a-z]+\b|"
    r"\brunners?[- ]?up\b|\bmedalist\b|\btop .*player\b|"
    r"\bstate meet\b|\bschool(?:.*?)record\b|\bteam record\b|"
    r"\branked (?:as high|.*(?:state|nation|region|player))\b|"
    r"\bnationals qualifier\b|\bnational qualifier\b|\bjunior nationals\b|"
    r"\byouth .*nationals\b|\bhigh school nationals\b|\byouth worlds\b|"
    r"\bhead of the charles\b|\bhead of the river\b|\bhenley\b|\berg\b|"
    r"\bboat club\b|\byouth singles\b|"
    r"\bECNL\b|\bMLS Next\b|\bILCA\b|\bFAA league\b|\bTVL\b|"
    r"\bstrikeouts?\b|\btackles?\b|\b(?:career |scored )?[\d,]+\s+points?\b|"
    r"\b(?:fly|5k)\s+record\b|^Club\s*:)"
)

ACADEMIC_CONTEXT_RE = re.compile(
    r"(?i)\b(scholarship|national merit|presidential scholar|coca-cola|"
    r"honor society|honors society|research|science fair|olympiad|history day|"
    r"academic competition|case study|stock pitch|valedictorian|salutatorian)\b"
)

LEVEL_RANK = {
    "unknown": 0,
    "participation": 1,
    "school": 2,
    "regional": 3,
    "state": 4,
    "national": 5,
    "international": 6,
}

SUBCATEGORY = {
    "academic_olympiad": "academic competitions",
    "research_science_fair": "research and science fairs",
    "robotics_engineering": "robotics and engineering",
    "cs_projects_competitions": "computing projects and competitions",
    "debate_speech": "debate, speech, or Model UN",
    "entrepreneurship": "business and entrepreneurship",
    "community_civic": "community service and civic leadership",
    "arts_music": "arts and music",
    "writing_media": "writing, journalism, and student media",
    "varsity_sport": "high-school athletics",
    "employment_family": "employment",
    "maker_building": "design and making",
    "student_government_leadership": "student government and leadership",
    "other": "academic honors and other activities",
}


def external(
    category,
    subcategory,
    level,
    achievement,
    evidence_url,
    confidence="high",
):
    return {
        "category": category,
        "subcategory": subcategory,
        "level": level,
        "achievement": achievement,
        "evidence_url": evidence_url,
        "_confidence": confidence,
        "_independent": True,
    }


ENRICHMENTS = {
    "Chloe Xu": [
        external(
            "other",
            "academic distinction",
            "school",
            "Named a 2024 Foothill High School co-valedictorian.",
            "https://www.independentnews.com/news/education_news/pleasanton-s-top-academics-share-thoughts-ahead-of-graduation/article_ade0298c-1e4d-11ef-bf51-ebf31644cce9.html",
        ),
        external(
            "maker_building",
            "Destination Imagination",
            "participation",
            "Participated in Destination Imagination STEAM challenges and tournaments.",
            "https://www.independentnews.com/news/education_news/pleasanton-s-top-academics-share-thoughts-ahead-of-graduation/article_ade0298c-1e4d-11ef-bf51-ebf31644cce9.html",
        ),
    ],
    "Caiden Lung": [
        external(
            "research_science_fair",
            "AI and health research",
            "regional",
            "Conducted research on AI-based COVID-19 treatment and presented it at the Long Island Science and Engineering Fair.",
            "https://www.liherald.com/lynbrook/stories/lynbrook-high-school-valedictorian,208380",
        ),
        external(
            "other",
            "academic distinction",
            "school",
            "Named valedictorian of Lynbrook High School's Class of 2024.",
            "https://www.liherald.com/lynbrook/stories/lynbrook-high-school-valedictorian,208380",
        ),
    ],
    "Laila Salgado": [
        external(
            "academic_olympiad",
            "climate science",
            "international",
            "International Climate Science Olympiad semifinalist.",
            "https://www.opschools.org/aboutus/news/class-of-2024-top-10",
        ),
        external(
            "community_civic",
            "sustainability and service",
            "regional",
            "Founded and led the Sustainability Club, served as an Erie County Climate Ambassador, and organized community-service work.",
            "https://www.opschools.org/aboutus/news/class-of-2024-top-10",
        ),
    ],
    "Maggie Feng": [
        external(
            "other",
            "scholarship",
            "state",
            "Received a 2024 Herb Kohl Foundation Excellence Scholarship.",
            "https://www.elmbrookschools.org/news-details/~board/district-news/post/2024-herb-kohl-foundation-award-recipients-announced",
        )
    ],
    "Rachel Yang": [
        external(
            "research_science_fair",
            "machine learning and cancer detection",
            "unknown",
            "Co-authored a 2024 study developing machine-learning models for colorectal-cancer detection using metabolites.",
            "https://doi.org/10.3390/cimb46050254",
            "medium",
        )
    ],
    "Sophia Woodbury": [
        external(
            "robotics_engineering",
            "FIRST Robotics",
            "school",
            "Served as president of FRC Team 8753, managing six sub-teams and more than 85 students.",
            "https://selbyfdn.org/sophia-woodbury-led-the-team-at-spectre-robotics/",
        )
    ],
    "Angela Zheng": [
        external(
            "robotics_engineering",
            "FIRST Robotics",
            "international",
            "Reported a Johnson Division playoff runner-up finish at the 2024 FIRST Robotics World Championships.",
            "https://www.ncsasports.org/womens-soccer-recruiting/ohio/lewis-center/olentangy-orange-high-school/angela-zheng1",
            "medium",
        )
    ],
    "Jonathan Wang": [
        external(
            "research_science_fair",
            "biomedical engineering",
            "state",
            "Tied for fourth in biomedical engineering at the Texas state science fair and received the Regeneron Biomedical Science Award.",
            "https://ghs.gcisd.net/o/ghs/article/1493176",
        )
    ],
    "Mia Rozenberg": [
        external(
            "research_science_fair",
            "translational medical science",
            "international",
            "Advanced to the 2025 Regeneron ISEF with a nanoparticle RNA-therapy delivery project.",
            "https://www.pinecrest.edu/news/2025-05-29/pine-crest-upper-school-science-research-students-present-at-isef",
        )
    ],
    "Saskia Poldmaa": [
        external(
            "research_science_fair",
            "physics and astronomy",
            "international",
            "Won a third grand award in Physics and Astronomy at the 2025 Regeneron ISEF.",
            "https://www.societyforscience.org/press-release/regeneron-isef-2025-full-awards/",
        )
    ],
    "Maddy Noll": [
        external(
            "other",
            "scholarship",
            "national",
            "Named a 2024 National Merit $2,500 Scholarship winner.",
            "https://www.dailyherald.com/20240514/submitted-content/local-winners-of-national-merit-2500-scholarships-named/",
        )
    ],
    "Katie Driscoll": [
        external(
            "research_science_fair",
            "nuclear-physics instrumentation",
            "participation",
            "Presented a Yale Wright Laboratory summer project on designing and assembling a dark box for scintillating-tile analysis.",
            "https://physics.yale.edu/event/wl-summer-symposium-2024-and-closing-luncheon",
        )
    ],
    "Marin Caiola": [
        external(
            "research_science_fair",
            "environmental-health research",
            "participation",
            "Worked as a research assistant and laboratory intern at NYU's Department of Medicine on an obesogen-exposure study.",
            "https://pelhamexaminer.com/71716/showcase/pmhs-seniors-marin-caiola-maddie-horner-charles-johnson-and-grace-kiamie-named-rotary-scholars-of-the-month/",
        ),
        external(
            "community_civic",
            "STEM outreach",
            "school",
            "Started the We Are STEM after-school program for younger girls.",
            "https://pelhamexaminer.com/71716/showcase/pmhs-seniors-marin-caiola-maddie-horner-charles-johnson-and-grace-kiamie-named-rotary-scholars-of-the-month/",
        ),
    ],
    "Nathan Wu": [
        external(
            "research_science_fair",
            "machine learning and melanoma",
            "international",
            "Qualified for the 2024 Regeneron ISEF with a science-fair coding project.",
            "https://www.ozarkssportszone.com/2024/10/31/athlete-of-the-week-nathan-wu-greenwood-swimming/",
            "medium",
        )
    ],
    "Samantha Moorhead": [
        external(
            "other",
            "academic distinction",
            "national",
            "Named a National Merit Commended Student.",
            "https://www.glenbard87.org/news/glenbard-news-for-oct-15-2024/",
        )
    ],
    "Lucy Vanderhoff": [
        external(
            "writing_media",
            "journalism",
            "national",
            "Selected as Kentucky's 2024 Al Neuharth Free Spirit and Journalism Scholar.",
            "https://www.freedomforum.org/about-freedom-forum/media-advisory/2024-06-17/",
        )
    ],
    "Carley Chen": [
        external(
            "other",
            "U.S. Presidential Scholars Program",
            "national",
            "Named a 2025 U.S. Presidential Scholars Program semifinalist.",
            "https://www.ed.gov/media/document/2025-psp-semifinalist-list-109853.pdf",
        )
    ],
    "Bill Chen": [
        external(
            "other",
            "academic distinction",
            "national",
            "Named a National Merit finalist and Rye High School salutatorian.",
            "https://resources.finalsite.net/images/v1750187156/ryeschoolsorg/d5pdncr58wrvhlldfkgo/Rye_HS_Graduation2025V2.pdf",
        )
    ],
    "Hunter Liao": [
        external(
            "research_science_fair",
            "game design and health screening",
            "participation",
            "Reported a George Mason University research project using gamified spatial navigation for Alzheimer's screening.",
            "https://www.linkedin.com/in/hunterliao",
            "medium",
        )
    ],
    "Parker Yates": [
        external(
            "research_science_fair",
            "behavioral science",
            "regional",
            "Received a USAID Science Champion Award in behavioral sciences.",
            "https://www.harrisoncsd.org/district/news-and-information/newsletters/district-newsletter-science-spring-2024",
        )
    ],
    "Kayla Han": [
        external(
            "community_civic",
            "health education and HOSA",
            "regional",
            "Spoke at TEDxYouth@UCVTS and served as NJ HOSA's Member-at-Large.",
            "https://www.ted.com/tedx/events/49020",
        )
    ],
    "Jayden Lin": [
        external(
            "cs_projects_competitions",
            "Amazon Future Engineer",
            "national",
            "Selected as a 2025 Amazon Future Engineer Scholarship winner.",
            "https://www.amazonfutureengineer.com/document-2025-afe-scholarship-us-winners",
        )
    ],
    "David Oladosu": [
        external(
            "other",
            "Delaware Secretary of Education Scholar",
            "state",
            "Selected as a 2025 Delaware Secretary of Education Scholar.",
            "https://education.delaware.gov/award-programs/secretary-of-education-scholars/2025-delaware-secretary-of-education-scholars/david-oladosu/",
        ),
        external(
            "student_government_leadership",
            "student government",
            "school",
            "Participated in Student Government, Math League, and the Technology Student Association.",
            "https://education.delaware.gov/award-programs/secretary-of-education-scholars/2025-delaware-secretary-of-education-scholars/david-oladosu/",
        ),
    ],
    "Molly Mascardo": [
        external(
            "research_science_fair",
            "glycobiology",
            "participation",
            "Completed University of Utah research on heparin precursor oligosaccharides and received Waterford's Science Department Prize.",
            "https://waterfordschool.org/blog/upper-school-closing-award-ceremony-2024/",
        ),
        external(
            "community_civic",
            "STEM outreach",
            "school",
            "Co-founded a club that taught science classes and supported girls interested in STEM.",
            "https://waterfordschool.org/blog/upper-school-closing-award-ceremony-2024/",
        ),
    ],
    "Ainsley Buice": [
        external(
            "arts_music",
            "chorus",
            "state",
            "Selected for the 2024 All-Virginia Chorus.",
            "https://fairfaxhs.fcps.edu/features/all-virginia-music-students",
        ),
        external(
            "community_civic",
            "food-insecurity service",
            "regional",
            "Baked more than 7,000 muffins for a local food-assistance program.",
            "https://m.burkeconnection.com/news/2025/jun/18/fairfax-high-honors-four-outstanding-students/",
        ),
    ],
    "Kaden Fenno": [
        external(
            "other",
            "academic scholarship",
            "school",
            "Received TMI Episcopal's Gresham Scholarship for academics, leadership, character, and extracurricular involvement.",
            "https://tminewsroom.com/2021/02/13/rising-9th-grade-alkek-gresham-and-frost-scholars/",
        )
    ],
    "Thomas Ludecke": [
        external(
            "maker_building",
            "design lab",
            "school",
            "Selected as a D!Lab intern and trained to use a 3D printer, laser cutter, and milling machine for independent projects.",
            "https://www.saes.org/news-detail?pk=1351552",
        )
    ],
    "William Knowlton": [
        external(
            "community_civic",
            "Scouting, FFA, and food-bank service",
            "regional",
            "Received the 2025 Scotty Scott Outstanding Citizen Award after documenting service through Scouting, NHS, and FFA, including a charity garden for a food bank.",
            "https://wyopreps.com/scotty-scott-awards-shrine-bowl-2025/",
        )
    ],
    "Natalia Medici": [
        external(
            "other",
            "academic distinction",
            "national",
            "Named a 2025 National Merit Finalist.",
            "https://www.alder.k12.oh.us/article/2087909",
        )
    ],
    "Ethan Geary": [
        external(
            "academic_olympiad",
            "school math and science teams",
            "school",
            "Participated in Metuchen High School's Math Team and Science Team.",
            "https://metuchenhsmedia.wixsite.com/home/post/senior-spotlight-ethan-geary",
        )
    ],
    "Anirudh Chari": [
        external(
            "research_science_fair",
            "autonomous-vehicle motion planning",
            "national",
            "Won a 2023 Davidson Fellows $10,000 scholarship for a multi-agent motion-planning algorithm.",
            "https://www.davidsongifted.org/gifted-programs/fellows-scholarship/fellows/current-and-past-fellows/2023-fellows/2023-davidson-fellow-anirudh-chari/",
        )
    ],
    "Alec Zhang": [
        external(
            "varsity_sport",
            "fencing",
            "participation",
            "Practiced competitive épée fencing from seventh grade through high school.",
            "https://harkeraquila.com/79630/humans-of-harker/class-of-2024/humans-of-harker-computing-lifes-next-move/",
        )
    ],
    "Amara Ukomadu": [
        external(
            "varsity_sport",
            "soccer",
            "school",
            "Served as a Brookline High School girls' soccer captain.",
            "https://thecypressonline.com/50621/sports/meet-the-2024-fall-captains-girls-soccer/",
        )
    ],
    "Kevin Zhang": [
        external(
            "varsity_sport",
            "football",
            "participation",
            "Played football at Flintridge Preparatory School and committed to continue at MIT.",
            "https://www.pasadenanow.com/pasadenaschools/flintridge-prep-top-student-athletes-commit-to-play-in-college/",
        )
    ],
    "Pavan Yeddanapudi": [
        external(
            "varsity_sport",
            "football",
            "regional",
            "Played center for Mountain House High School and was named a second-team Western Athletic Conference offensive lineman.",
            "https://www.ttownmedia.com/tracy_press/sports/football-mustangs-determined-to-learn-from-their-mistakes/article_8e8a1ab6-3249-11ee-b0c1-331502065de0.html",
            "medium",
        )
    ],
    "Paulius Karvelis": [
        external(
            "varsity_sport",
            "basketball",
            "school",
            "Played shooting guard, small forward, and power forward for Lake Forest Academy in 2024-25.",
            "https://spectator.lfanet.org/10989/sports/senior-sports-commitments-class-of-2025-sign-off/",
        )
    ],
    "Francesca Garfi": [
        external(
            "varsity_sport",
            "basketball",
            "school",
            "Played varsity basketball for Pine Crest School.",
            "https://www.ncsasports.org/womens-basketball-recruiting/florida/fort-lauderdale/pine-crest-school/francesca-garfi1",
            "medium",
        ),
        external(
            "student_government_leadership",
            "student government",
            "school",
            "Reported serving in student government, including as class president and steering head.",
            "https://www.linkedin.com/in/francesca-garfi-3bb760276",
            "medium",
        ),
    ],
    "Chidubem Chukwu": [
        external(
            "varsity_sport",
            "track and field",
            "regional",
            "Competed for Noble and Greenough at ISL and NEPSTA track and field championships.",
            "https://www.directathletics.com/athletes/track/8173106.html",
        ),
        external(
            "debate_speech",
            "Model United Nations",
            "school",
            "Reported serving as an Under-Secretary General for Noble and Greenough's Model UN conference.",
            "https://www.linkedin.com/in/chidubem-chukwu-78ba21388",
            "medium",
        ),
    ],
    "Sarah Hopp": [
        external(
            "varsity_sport",
            "cross country",
            "regional",
            "Competed for Stevens Point in the 2021 WIAA Division 1 sectional cross-country meet.",
            "https://www.wiaawi.org/Portals/0/PDF/Results/Cross_Country/2021/d1gspashsectional.pdf?ver=3NEm_a_9nkA1L8bY_SeZ-g%3D%3D",
        ),
        external(
            "student_government_leadership",
            "student senate",
            "school",
            "Reported participation in Student Senate and student mentoring.",
            "https://www.linkedin.com/in/sarah-hopp-01537827b",
            "medium",
        ),
    ],
}

ENRICHMENTS.update(
    {
        "Aaron Martin": [
            external(
                "other",
                "U.S. Presidential Scholars Program",
                "national",
                "Named a 2024 U.S. Presidential Scholars Program candidate.",
                "https://www.ed.gov/media/document/2024-awards-candidates-us-presidential-scholars-program-74333.pdf",
            )
        ],
        "Anjalina Thomas": [
            external(
                "other",
                "academic distinction",
                "state",
                "Named an Oklahoma Academic All-State honoree and National Merit Finalist.",
                "https://www.cvtech.edu/cv-tech-pre-engineering-student-accepted-to-mit/",
            )
        ],
        "Anselma Petrie": [
            external(
                "other",
                "academic distinction",
                "school",
                "Named valedictorian of Eastchester High School's Class of 2024.",
                "https://www.eufsdk12.org/fs/resource-manager/view/04526066-0e92-4c0c-b4aa-6753bedf0e0d",
            )
        ],
        "Avi Narula": [
            external(
                "community_civic",
                "hunger and homelessness service",
                "regional",
                "Named to Atlanta's 2023 20 Under 20 list for sustained service addressing hunger and homelessness.",
                "https://www.paceacademy.org/post-detail/~board/pace-news/post/merchant-narula-named-to-20-under-20",
            )
        ],
        "Jacob Dell": [
            external(
                "community_civic",
                "school leadership",
                "school",
                "Documented as class valedictorian and Key Club president by the National Football Foundation's Greater Baltimore chapter.",
                "https://www.nffbaltimore.com/2024",
            )
        ],
        "Taylor McAndrew": [
            external(
                "other",
                "academic distinction",
                "national",
                "Named a 2024 National Merit Commended Student.",
                "https://eastonmaschools.org/three-oliver-ames-high-school-seniors-commended-by-national-merit-scholarship-program/",
            ),
            external(
                "student_government_leadership",
                "student council",
                "school",
                "Served as Oliver Ames High School Student Council president.",
                "https://eastonmaschools.org/three-oliver-ames-high-school-seniors-commended-by-national-merit-scholarship-program/",
            ),
        ],
        "Varun Ravilla": [
            external(
                "other",
                "academic distinction",
                "national",
                "Named a National Merit Semifinalist by Coppell ISD.",
                "https://www.coppellisd.com/article/1239837",
            )
        ],
        "Bari LeBari": [
            external(
                "other",
                "academic distinction",
                "school",
                "Named salutatorian of Harvard-Westlake's Class of 2024.",
                "https://hwchronicle.com/109493/news/2024-student-awards-announced/",
            )
        ],
        "Isaac Torchinsky-Field": [
            external(
                "other",
                "scholarship",
                "national",
                "Named a 2025 National Merit Scholar.",
                "https://www.inquirer.com/education/national-merit-scholars-2025-philadelphia-20250507.html",
            )
        ],
        "James Lukish": [
            external(
                "other",
                "academic scholarship",
                "school",
                "Received a four-year Knott Scholarship and Loyola Blakefield's award for the graduating student with the highest mid-senior-year GPA.",
                "https://www.loyolablakefield.org/news-detail?pk=1574170",
            ),
            external(
                "community_civic",
                "school service",
                "school",
                "Led a school food-pantry effort that collected more than 25,000 items and served as vice president for service.",
                "https://www.loyolablakefield.org/news-detail?pk=1574707",
            ),
        ],
        "Lauren Sundquist": [
            external(
                "other",
                "academic distinction",
                "national",
                "Recognized as a National Merit Scholarship Finalist and Gladstone High School's outstanding math student.",
                "https://www.dailypress.net/news/community/2025/06/gladstone-graduates-received-awards-and-scholarships/",
            )
        ],
        "Mairin Anderson": [
            external(
                "other",
                "academic distinction",
                "school",
                "Received The Rivers School Mathematics Prize and was elected to the Cum Laude Society.",
                "https://www.rivers.org/news-detail?pk=1383694",
            )
        ],
        "Mason Prettyman": [
            external(
                "other",
                "academic distinction",
                "national",
                "Named a 2025 National Merit Scholarship Program semifinalist.",
                "https://hs.mtlsd.org/about/school-news/details/~board/high-school-news/post/terrific-10-mtlsd-students-named-semifinalists-in-the-national-merit-scholarship-program",
            )
        ],
        "Rishabh Sharma": [
            external(
                "other",
                "academic distinction",
                "school",
                "Recognized as valedictorian of Episcopal High School's Class of 2025.",
                "https://www.ehshouston.org/about/news/newspost/~board/migrated-news/post/sharma-awarded-spence-trophy",
            )
        ],
        "Ava Thigpen": [
            external(
                "other",
                "academic distinction",
                "national",
                "Named a 2025 National Merit Semifinalist.",
                "https://www.hockaday.org/news-detail?pk=1523653",
            )
        ],
        "Caden Wong": [
            external(
                "other",
                "academic distinction",
                "national",
                "Named a 2025 National Merit Commended Student.",
                "https://www.bhpsnj.org/o/glhs/article/1826887",
            )
        ],
        "Colton Pozniak": [
            external(
                "other",
                "standardized-test distinction",
                "national",
                "Earned a perfect composite score of 36 on the ACT.",
                "https://www.kimberly.k12.wi.us/departments/communications/news/1788650/kimberly-high-school-student-colton-pozniak-earned-a-perfect-score-on-the-act",
            )
        ],
        "Logan Yee": [
            external(
                "other",
                "academic distinction",
                "school",
                "Inducted into the Charlotte Latin School chapter of the Cum Laude Society.",
                "https://www.charlottelatin.org/about/school-news/news-details/~board/news/post/charlotte-latin-students-inducted-into-cum-laude-society",
            )
        ],
        "Rayna Li": [
            external(
                "other",
                "academic distinction",
                "national",
                "Named a 2025 National Merit Semifinalist.",
                "https://www.hockaday.org/news-detail?pk=1523653",
            ),
            external(
                "other",
                "academic distinction",
                "school",
                "Inducted into The Hockaday School's Cum Laude Society.",
                "https://www.hockaday.org/news-detail?pk=1567431",
            ),
        ],
        "Sophia Guerra": [
            external(
                "other",
                "academic distinction",
                "national",
                "Named a 2025 National Merit Finalist by Plano ISD.",
                "https://www.pisd.edu/news-events/plano-isd-headlines/2024-25-photos-and-news/2025-national-merit-finalists",
            )
        ],
        "Nicolette Xydas": [
            external(
                "research_science_fair",
                "science recognition",
                "regional",
                "Selected as Carrollton School's 2025 Silver Knight nominee in science.",
                "https://www.carrollton.org/school-news/dynamic-post-page/~board/school-news/post/celebrating-carrolltons-2025-silver-knight-nominees",
            )
        ],
    }
)

ENRICHMENTS["Samantha Moorhead"].append(
    external(
        "other",
        "U.S. Presidential Scholars Program",
        "national",
        "Named a 2025 U.S. Presidential Scholars Program semifinalist.",
        "https://www.ed.gov/media/document/2025-psp-semifinalist-list-109853.pdf",
    )
)


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def infer_category(item):
    for category, pattern in CATEGORY_PATTERNS:
        if pattern.search(item):
            return category
    if SPORT_RE.search(item):
        return "varsity_sport"
    if BROAD_SPORT_RE.search(item) and not ACADEMIC_CONTEXT_RE.search(item):
        return "varsity_sport"
    return "other"


def infer_level(item):
    text = item.lower()
    level_text = re.sub(
        r"\b(?:(?:science|math(?:ematics)?|english|spanish|art|technical|"
        r"social studies|world language)\s+)?national honors? societ(?:y|ies)\b",
        "honor society",
        text,
    )
    level_text = re.sub(
        r"\bnational (?:(?:science|math(?:ematics)?|english|spanish|art|technical|"
        r"social studies|world language)\s+)?honors? societ(?:y|ies)\b",
        "honor society",
        level_text,
    )
    if any(
        term in level_text
        for term in (
            "international",
            "world championship",
            "world championships",
            "youth worlds",
            "isef",
            "north american champion",
        )
    ):
        return "international"
    if any(
        term in level_text
        for term in (
            "national",
            "all-american",
            "presidential scholar",
            "usamo",
            "usabo",
            "usnco",
            "aime",
            "gates scholar",
            "ap scholar",
        )
    ):
        return "national"
    if any(
        term in level_text
        for term in ("all-state", "state champion", "state champs", " state ", "state-level")
    ):
        return "state"
    if any(
        term in level_text
        for term in (
            "regional",
            "conference",
            "all-county",
            "district",
            "sectional",
            "all-league",
            "county",
            "city",
        )
    ):
        return "regional"
    if any(
        term in level_text
        for term in (
            "varsity",
            "captain",
            "president",
            "vice president",
            "valedictorian",
            "salutatorian",
            "honor society",
            "school",
            "club",
        )
    ):
        return "school"
    if any(term in level_text for term in ("participant", "member", "intern", "volunteer")):
        return "participation"
    return "unknown"


def grouped_mit_activities(person):
    by_category = defaultdict(list)
    high_school = clean(person.get("high_school")).casefold()
    for raw_item in person.get("before_mit_items", []):
        item = clean(raw_item)
        if (
            not item
            or NOISE_RE.search(item)
            or SENSITIVE_RE.search(item)
            or item.casefold() == high_school
        ):
            continue
        by_category[infer_category(item)].append(item)

    activities = []
    evidence_url = person["memberships"][0]["profile_url"]
    for category, items in by_category.items():
        ranked = sorted(
            enumerate(items),
            key=lambda pair: (LEVEL_RANK[infer_level(pair[1])], -pair[0]),
            reverse=True,
        )
        selected = [item for _, item in ranked[:3]]
        level = max((infer_level(item) for item in selected), key=LEVEL_RANK.get)
        activities.append(
            {
                "category": category,
                "subcategory": SUBCATEGORY[category],
                "level": level,
                "achievement": "; ".join(selected),
                "evidence_url": evidence_url,
                "_confidence": "high",
                "_independent": False,
            }
        )
    return activities


def public_activity(activity):
    return {
        key: activity[key]
        for key in ("category", "subcategory", "level", "achievement", "evidence_url")
    }


def choose_flagship(activities):
    category_tiebreak = {
        "research_science_fair": 8,
        "academic_olympiad": 7,
        "robotics_engineering": 6,
        "cs_projects_competitions": 6,
        "debate_speech": 5,
        "entrepreneurship": 5,
        "community_civic": 4,
        "arts_music": 4,
        "writing_media": 4,
        "varsity_sport": 3,
        "student_government_leadership": 3,
        "maker_building": 3,
        "employment_family": 2,
        "other": 1,
    }
    return max(
        activities,
        key=lambda activity: (
            LEVEL_RANK[activity["level"]],
            1 if activity.get("_independent") else 0,
            category_tiebreak.get(activity["category"], 0),
        ),
    )


def host(url):
    return urlparse(url).netloc.lower().removeprefix("www.")


def main():
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    records = []
    included_names = set()
    retained_no_activity = []

    for person in inventory["people"]:
        if person["already_in_csv"]:
            continue

        mit_activities = grouped_mit_activities(person)
        independent_activities = ENRICHMENTS.get(person["person_name"], [])
        if independent_activities:
            # Curated independent evidence replaces MIT-only non-athletic groups to
            # avoid duplicate claims while retaining official high-school sport claims.
            sport_activities = [
                activity
                for activity in mit_activities
                if activity["category"] == "varsity_sport"
            ]
            activities = sport_activities + independent_activities
        else:
            activities = mit_activities

        if activities:
            flagship = choose_flagship(activities)
        else:
            retained_no_activity.append(person["person_name"])
            flagship = None
        membership_teams = sorted(
            {membership["team"] for membership in person["memberships"]}
        )
        roster_urls = sorted(
            {membership["roster_url"] for membership in person["memberships"]}
        )
        profile_urls = sorted(
            {membership["profile_url"] for membership in person["memberships"]}
        )
        external_urls = sorted(
            {
                activity["evidence_url"]
                for activity in independent_activities
                if activity["evidence_url"] not in roster_urls + profile_urls
            }
        )
        source_urls = profile_urls + roster_urls + external_urls

        categories = {activity["category"] for activity in activities}
        if not activities:
            stratum = "no-documented-precollege-activity"
        elif categories == {"varsity_sport"}:
            stratum = "pure-athletics"
        else:
            stratum = "multi-activity"
        independent_nonathletic = [
            activity
            for activity in independent_activities
            if activity["category"] != "varsity_sport"
        ]
        explicit_debate = [
            activity["achievement"]
            for activity in activities
            if re.search(r"(?i)\bdebate\b|speech team|speech and debate", activity["achievement"])
        ]
        if explicit_debate:
            debate = "yes"
            debate_details = "; ".join(explicit_debate)
        else:
            debate = "no_documented" if mit_activities else "unknown"
            debate_details = None

        if not activities:
            enrichment_note = (
                "No pre-college activity was found in the retained public evidence; "
                "the verified roster profile is preserved to avoid visibility-based selection."
            )
        elif independent_nonathletic:
            enrichment_note = (
                "Independent non-athletic enrichment retained from "
                + ", ".join(sorted({host(a["evidence_url"]) for a in independent_nonathletic}))
                + "."
            )
        elif independent_activities:
            enrichment_note = (
                "External evidence was used only to establish a high-school sport activity; "
                "no independently sourced non-athletic achievement was retained."
            )
        else:
            enrichment_note = (
                "No independent non-athletic source was retained in the targeted public-source "
                "review; claims come from the official MIT athlete biography."
            )

        note = (
            "Sampling frame: MIT athletics roster. "
            f"MIT team(s): {'; '.join(membership_teams)}. "
            f"Activity stratum: {stratum}. "
            "Class year mapped from official current-roster standing "
            f"({person['memberships'][0]['roster_class']}="
            f"{person['mit_class_year']}); high-school graduation year was not inferred. "
            "Name was absent from the normalized-name index of the supplied "
            "mit-ready-research/data/mit_students.csv. "
            + enrichment_note
        )

        record = {
            "record_type": "mit_student",
            "person_name": person["person_name"],
            "mit_status": "current_undergrad",
            "mit_class_year": person["mit_class_year"],
            "mit_evidence_url": profile_urls[0],
            "high_school": person.get("high_school"),
            "hs_grad_year": None,
            "activities": [public_activity(activity) for activity in activities],
            "flagship_category": flagship["category"] if flagship else "unknown",
            "flagship_signal": flagship["achievement"] if flagship else "unknown",
            "flagship_confidence": flagship["_confidence"] if flagship else "low",
            "debate": debate,
            "debate_details": debate_details,
            "source_urls": source_urls,
            "notes": note,
        }
        records.append(record)
        included_names.add(person["normalized_name"])

    records.sort(key=lambda row: (row["mit_class_year"], row["person_name"].casefold()))
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")

    class_counts = Counter(row["mit_class_year"] for row in records)
    confidence_counts = Counter(row["flagship_confidence"] for row in records)
    stratum_counts = Counter(
        (
            "no-documented-precollege-activity"
            if not row["activities"]
            else (
                "pure-athletics"
                if {activity["category"] for activity in row["activities"]}
                == {"varsity_sport"}
                else "multi-activity"
            )
        )
        for row in records
    )
    team_counts = Counter()
    for person in inventory["people"]:
        if person["normalized_name"] not in included_names:
            continue
        for membership in person["memberships"]:
            team_counts[membership["team"]] += 1
    all_team_labels = sorted(
        {
            membership["team"]
            for person in inventory["people"]
            for membership in person["memberships"]
        }
    )
    complete_team_counts = {team: team_counts.get(team, 0) for team in all_team_labels}

    summary = {
        "output": str(OUTPUT),
        "rows": len(records),
        "by_class": dict(sorted(class_counts.items())),
        "by_team": complete_team_counts,
        "by_activity_stratum": dict(sorted(stratum_counts.items())),
        "by_flagship_confidence": dict(sorted(confidence_counts.items())),
        "independently_enriched_nonathletic": sum(
            "Independent non-athletic enrichment retained" in row["notes"]
            for row in records
        ),
        "roster_unique_underclass": inventory["unique_underclass_people"],
        "excluded_existing_csv": inventory["already_in_csv"],
        "retained_without_precollege_activity_evidence": len(retained_no_activity),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
