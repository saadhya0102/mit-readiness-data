import csv
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(r"C:\Users\hasto\Demo Projects")
CSV_PATH = ROOT / "mit-ready-research" / "data" / "mit_students.csv"
OUTPUT_PATH = ROOT / "mit_worker_32_stem_crossmatch.jsonl"

ALLOWED_CATEGORIES = {
    "academic_olympiad",
    "research_science_fair",
    "robotics_engineering",
    "cs_projects_competitions",
    "debate_speech",
    "entrepreneurship",
    "community_civic",
    "arts_music",
    "writing_media",
    "varsity_sport",
    "employment_family",
    "maker_building",
    "student_government_leadership",
    "other",
}

SELECTIONS = {
    "mit_worker_12_science_fair.jsonl": {
        "Angie Ayoubi",
        "Naomi Park",
        "Saathvik Kannan",
    },
    "mit_worker_24_linkedin_gl.jsonl": {
        "Melat Ghebreselassie",
        "Irene Jiang",
        "Priyanka Karunakaran",
        "Melissa Li",
        "Tina Li",
        "Audrey Lin",
        "Anna Hung",
        "Ania Kelly",
        "SangHyuk Im",
        "Paddy Garman",
        "Brian Li",
        "Ruiyang (Raymond) Luo",
        "David Lomelin",
        "Ittai Kohavi",
    },
    "mit_worker_26_linkedin_sz.jsonl": {
        "Andy Yang",
        "Nathan Wu",
        "Angela Zheng",
        "Kaitlyn Strine",
        "Chloe Xu",
        "Maya Zavatsky",
        "Jonathan Wang",
        "Laila Salgado",
        "Kevin Zheng",
    },
    "mit_worker_28_labs_programs.jsonl": {
        "Graciela Rodriguez",
        "Emily Alemán",
        "Angelina Costa",
        "Lauren Stelwagon",
        "Ellery McDaniel",
        "Ajibola Ajani",
        "Ashlyn Gao",
    },
    "mit_worker_29_underclass_athletics.jsonl": {
        "AJ Sachwitz",
        "Anirudh Chari",
        "Anna Hung",
        "Ben Wu",
        "Caiden Lung",
        "Delaney Benevides",
        "Fiona Lee",
        "Griffin Patterson",
        "Jack Wang",
        "Laila Salgado",
        "Michael Bailey",
        "Molly Mascardo",
        "Sophia Woodbury",
        "Zoe Barton",
        "Alexia Ninios",
        "Angela Zheng",
        "Anna Gluschuk",
        "Carter Magnano",
        "Evan Wong",
        "Hayato Nagai",
        "Ian Sun",
        "Jayden Lin",
        "Jonathan Wang",
        "Joshua Tang",
        "Kaitlyn Strine",
        "Julia Mattiace",
        "Mia Rozenberg",
        "Milon Kalia",
        "Nathan Wu",
        "Nathaniel Black",
        "Nick Soule",
        "Nicolette Xydas",
        "Parker Yates",
        "Saskia Poldmaa",
        "Shriya Thakur",
        "Theo Perkins",
    },
    "mit_worker_30_news_geographic.jsonl": {
        "Sam Lizotte",
        "Helena Teltscher",
    },
    "mit_worker_34_linkedin_af.jsonl": {
        "Anirudh Chari",
        "Chloe Dai",
        "Nathaniel Black",
    },
    "mit_worker_36_linkedin_mr.jsonl": {
        "Anika Mittal",
        "Mia Rozenberg",
        "Marc Nichitiu",
        "Danny Pikovskiy",
        "Bolu Omole",
        "Ellery McDaniel",
        "Sarah Pan",
        "Angelina Quan",
        "Leen Qanash",
        "Ananeah Nevil",
        "Victoria Ou",
        "Donato Moakofhi",
        "Naomi Park",
        "Nidhi Nair",
        "Matthew Medina",
        "Mellanie Rodriguez",
        "Kelsey Morey",
    },
    "mit_worker_38_news_west_midwest.jsonl": {
        "Ishanvi Kommula",
        "Fiona Wang",
        "Molly Mascardo",
    },
    "mit_worker_39_news_international.jsonl": {
        "Zhi Zheng Ong",
        "Fidan Huseynova",
        "Jiyar Moslemi",
        "Siiri Roschier",
        "Isken Kenzhebaev",
        "Sevinj Mahmudova",
        "Leia Mayssa Masyerin",
    },
}

MIT_EVIDENCE_OVERRIDES = {
    "Angie Ayoubi": "https://www.sigmakappa.mit.edu/class-of-2028",
    "Saathvik Kannan": "https://gue.mit.edu/wp-content/uploads/2026/01/OVC-annualreport-2025.pdf",
    "Emily Alemán": "https://no6.scripts.mit.edu/directory/list?mit_year=2028",
    "Helena Teltscher": "https://dh.mit.edu/home/",
    "Ben Wu": "https://pkt.mit.edu/brothers/twentyeights/",
    "Paddy Garman": "https://phisig.mit.edu/brothers",
    "SangHyuk Im": "https://phisig.mit.edu/brothers",
    "Zhi Zheng Ong": "https://engage.mit.edu/MYSA/web_officers",
    "Fidan Huseynova": "https://no6.scripts.mit.edu/directory/list?mit_year=2028",
    "Jiyar Moslemi": "https://web.mit.edu/nolanlab/Nolan_Lab_Website/Members.html",
    "Siiri Roschier": "https://dh.mit.edu/home/",
    "Isken Kenzhebaev": "https://dh.mit.edu/home/",
    "Alexia Ninios": "https://www.theta.mit.edu/sisters-3",
    "Angela Zheng": "https://www.theta.mit.edu/sisters-3",
    "Ian Sun": "https://phisig.mit.edu/brothers",
    "Mia Rozenberg": "https://assistivetech.mit.edu/team/",
    "Milon Kalia": "https://kappasigma.mit.edu/brothers",
    "Nathan Wu": "https://phisig.mit.edu/brothers",
    "Sevinj Mahmudova": "https://uswim.mit.edu/people/",
    "Leia Mayssa Masyerin": "https://engage.mit.edu/MYSA/web_officers",
}

QUALIFYING_NAMES = {
    "Ali Alsaleh",
    "Alexia Ninios",
    "Ananeah Nevil",
    "Angelina Quan",
    "Angela Zheng",
    "Angie Ayoubi",
    "Anjali George",
    "Anthony Lin",
    "Audrey Lin",
    "Ben Wu",
    "Brian Li",
    "Chloe Yehwon Lee",
    "Danny Pikovskiy",
    "Donato Moakofhi",
    "Emily Alemán",
    "Fidan Huseynova",
    "Fiona Wang",
    "Grace Lin",
    "Irene Jiang",
    "Ishanvi Kommula",
    "Ishana Chadha",
    "Isken Kenzhebaev",
    "Jiyar Moslemi",
    "Kelsey Morey",
    "Leen Qanash",
    "Leia Mayssa Masyerin",
    "Marc Nichitiu",
    "Martin Meister",
    "Matthew Medina",
    "Melat Ghebreselassie",
    "Melissa Li",
    "Mia Rozenberg",
    "Milon Kalia",
    "Naomi Park",
    "Nathan Wu",
    "Paddy Garman",
    "Priyanka Karunakaran",
    "Ruiyang (Raymond) Luo",
    "Ryan Junsung Jang",
    "Saathvik Kannan",
    "Sam Lizotte",
    "Samuel Xu",
    "Sehoon Kang",
    "Sevinj Mahmudova",
    "Siiri Roschier",
    "Taohan Lin",
    "Victoria Ou",
    "Zhi Zheng Ong",
}


def normalize_name(name):
    folded = unicodedata.normalize("NFKD", name or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", folded.lower())


def activity(category, subcategory, level, achievement, evidence_url):
    return {
        "category": category,
        "subcategory": subcategory,
        "level": level,
        "achievement": achievement,
        "evidence_url": evidence_url,
    }


def supplemental_records():
    clubchem = "https://web.mit.edu/clubchem/www/execs.html"
    return [
        {
            "record_type": "mit_student",
            "person_name": "Sehoon Kang",
            "mit_status": "current_undergrad",
            "mit_class_year": 2028,
            "mit_evidence_url": clubchem,
            "high_school": "The Webb Schools",
            "hs_grad_year": 2024,
            "activities": [
                activity(
                    "research_science_fair",
                    "chemistry — Regeneron ISEF",
                    "international",
                    "Won a 2023 Regeneron ISEF Fourth Grand Award and an American Academy special award for metal-organic-framework catalysis research.",
                    "https://abstracts.societyforscience.org/Home/FullAbstract?AllAbstracts=False&Category=Any%20Category&FairCountry=Any%20Country&FairState=Any%20State&ProjectId=24031",
                )
            ],
            "flagship_category": "research_science_fair",
            "flagship_signal": "2023 Regeneron ISEF Chemistry Fourth Grand Award.",
            "flagship_confidence": "high",
            "debate": "no_documented",
            "debate_details": None,
            "source_urls": [
                clubchem,
                "https://abstracts.societyforscience.org/Home/FullAbstract?AllAbstracts=False&Category=Any%20Category&FairCountry=Any%20Country&FairState=Any%20State&ProjectId=24031",
            ],
            "notes": "MIT ClubChem lists Kang as Class of 2028 and from Korea; the ISEF record and matching public education history identify the Webb Schools finalist.",
        },
        {
            "record_type": "mit_student",
            "person_name": "Ali Alsaleh",
            "mit_status": "current_undergrad",
            "mit_class_year": 2028,
            "mit_evidence_url": clubchem,
            "high_school": None,
            "hs_grad_year": 2024,
            "activities": [
                activity(
                    "academic_olympiad",
                    "chemistry — International Chemistry Olympiad",
                    "international",
                    "Won a silver medal for Saudi Arabia at the 2023 International Chemistry Olympiad.",
                    "https://www.icho-official.org/results/results.php?id=55&year=2023",
                )
            ],
            "flagship_category": "academic_olympiad",
            "flagship_signal": "2023 International Chemistry Olympiad silver medalist.",
            "flagship_confidence": "medium",
            "debate": "no_documented",
            "debate_details": None,
            "source_urls": [
                clubchem,
                "https://www.icho-official.org/results/results.php?id=55&year=2023",
                "https://linkedin.com/in/ali-alsaleh-8b9544298",
            ],
            "notes": "MIT ClubChem supplies Class of 2028; the public MIT/KGSP chemistry profile supplies Saudi context linking the AlSaleh spelling used by IChO. Confidence is medium because the official sources use a spacing variant.",
        },
        {
            "record_type": "mit_student",
            "person_name": "Chloe Yehwon Lee",
            "mit_status": "current_undergrad",
            "mit_class_year": 2029,
            "mit_evidence_url": clubchem,
            "high_school": "Plano East Senior High School",
            "hs_grad_year": 2025,
            "activities": [
                activity(
                    "research_science_fair",
                    "chemistry — Regeneron STS",
                    "national",
                    "Named a 2025 Regeneron STS finalist for modifying acetaminophen to reduce liver toxicity and improve drug efficacy.",
                    "https://www.societyforscience.org/regeneron-sts/2025-student-finalists/chloe-lee/",
                ),
                activity(
                    "arts_music",
                    "violin and orchestra",
                    "regional",
                    "Served as school orchestra president and first violinist in the Greater Dallas Youth Orchestra.",
                    "https://www.societyforscience.org/regeneron-sts/2025-student-finalists/chloe-lee/",
                ),
            ],
            "flagship_category": "research_science_fair",
            "flagship_signal": "2025 Regeneron STS finalist in chemistry.",
            "flagship_confidence": "high",
            "debate": "no_documented",
            "debate_details": None,
            "source_urls": [
                clubchem,
                "https://www.societyforscience.org/regeneron-sts/2025-student-finalists/chloe-lee/",
            ],
            "notes": "MIT ClubChem lists Chloe Lee '29 from Texas; the STS profile gives the expanded name, Murphy/Plano context, chemistry focus, and 2025 graduation timing.",
        },
        {
            "record_type": "mit_student",
            "person_name": "Samuel Xu",
            "mit_status": "current_undergrad",
            "mit_class_year": 2029,
            "mit_evidence_url": "https://esp.mit.edu/teach/teachers/uxleumas/bio.html",
            "high_school": "Newton South High School",
            "hs_grad_year": 2025,
            "activities": [
                activity(
                    "academic_olympiad",
                    "chemistry — U.S. National Chemistry Olympiad",
                    "national",
                    "Selected as first alternate for the 2025 U.S. International Chemistry Olympiad team after attending the national study camp.",
                    "https://www.acs.org/pressroom/newsreleases/2025/june/2025-us-chemistry-olympians-named.html",
                )
            ],
            "flagship_category": "academic_olympiad",
            "flagship_signal": "First alternate for the 2025 U.S. International Chemistry Olympiad team.",
            "flagship_confidence": "high",
            "debate": "no_documented",
            "debate_details": None,
            "source_urls": [
                "https://esp.mit.edu/teach/teachers/uxleumas/bio.html",
                clubchem,
                "https://www.acs.org/pressroom/newsreleases/2025/june/2025-us-chemistry-olympians-named.html",
            ],
            "notes": "MIT ESP jointly states MIT Class of 2029 and Newton origin; ACS identifies the Newton South student.",
        },
        {
            "record_type": "mit_student",
            "person_name": "Anjali George",
            "mit_status": "current_undergrad",
            "mit_class_year": 2028,
            "mit_evidence_url": "https://uswim.mit.edu/people/",
            "high_school": "University School of Milwaukee",
            "hs_grad_year": 2024,
            "activities": [
                activity(
                    "academic_olympiad",
                    "mathematics — AIME",
                    "national",
                    "Qualified for the 2024 American Invitational Mathematics Examination.",
                    "https://www.usm.org/about/news/post/~board/2023-24/post/student-earns-perfect-score-in-math-competition",
                ),
                activity(
                    "academic_olympiad",
                    "team mathematics competition",
                    "regional",
                    "Competed on University School of Milwaukee's third-place team at the 2024 MSOE Opportunity Conference.",
                    "https://www.usm.org/about/news/post/~board/2023-24/post/student-earns-perfect-score-in-math-competition",
                ),
            ],
            "flagship_category": "academic_olympiad",
            "flagship_signal": "2024 AIME qualifier.",
            "flagship_confidence": "high",
            "debate": "no_documented",
            "debate_details": None,
            "source_urls": [
                "https://uswim.mit.edu/people/",
                "https://www.usm.org/about/news/post/~board/2023-24/post/student-earns-perfect-score-in-math-competition",
                "https://www.usm.org/about/news/post/~board/2023-24/post/usm-holds-class-of-2024-commencement",
            ],
            "notes": "MIT USWIM lists George '28; the school sources identify the same 2024 valedictorian and math competitor.",
        },
        {
            "record_type": "mit_student",
            "person_name": "Taohan Lin",
            "mit_status": "current_undergrad",
            "mit_class_year": 2028,
            "mit_evidence_url": "https://dh.mit.edu/home/",
            "high_school": "Thomas Jefferson High School for Science and Technology",
            "hs_grad_year": 2024,
            "activities": [
                activity(
                    "academic_olympiad",
                    "physics — USA Physics Olympiad",
                    "national",
                    "Received honorable mention in the 2024 USA Physics Olympiad.",
                    "https://www.aapt.org/physicsteam/2024/upload/2024-Medal-Listing_v2.pdf",
                ),
                activity(
                    "academic_olympiad",
                    "physics team leadership",
                    "school",
                    "Served as co-captain of the Thomas Jefferson physics team.",
                    "https://activities.tjhsst.edu/physics/past.html",
                ),
            ],
            "flagship_category": "academic_olympiad",
            "flagship_signal": "2024 USA Physics Olympiad honorable mention.",
            "flagship_confidence": "high",
            "debate": "no_documented",
            "debate_details": None,
            "source_urls": [
                "https://dh.mit.edu/home/",
                "https://www.aapt.org/physicsteam/2024/upload/2024-Medal-Listing_v2.pdf",
                "https://activities.tjhsst.edu/physics/past.html",
            ],
            "notes": "MIT German House lists Lin '28 from Northern Virginia; AAPT and TJ identify the same uncommon full name and school context.",
        },
        {
            "record_type": "mit_student",
            "person_name": "Martin Meister",
            "mit_status": "current_undergrad",
            "mit_class_year": 2029,
            "mit_evidence_url": "https://dh.mit.edu/home/",
            "high_school": "Centennial High School",
            "hs_grad_year": 2025,
            "activities": [
                activity(
                    "academic_olympiad",
                    "physics — USA Physics Olympiad",
                    "national",
                    "Received honorable mention in the 2025 USA Physics Olympiad.",
                    "https://aapt.org/physicsteam/2025/upload/2025-Honors-and-Distinction-List_v2.pdf",
                ),
                activity(
                    "research_science_fair",
                    "environmental biotechnology — BioGENEius",
                    "state",
                    "Won the 2024 Maryland BioGENEius Challenge with a machine-learning and remote-sensing seagrass-density project.",
                    "https://www.learningundefeated.org/news/learning-undefeated-announces-centennial-high-school-student-as-2024-maryland-biogeneius-finalist/",
                ),
            ],
            "flagship_category": "academic_olympiad",
            "flagship_signal": "2025 USA Physics Olympiad honorable mention.",
            "flagship_confidence": "high",
            "debate": "no_documented",
            "debate_details": None,
            "source_urls": [
                "https://dh.mit.edu/home/",
                "https://aapt.org/physicsteam/2025/upload/2025-Honors-and-Distinction-List_v2.pdf",
                "https://www.learningundefeated.org/news/learning-undefeated-announces-centennial-high-school-student-as-2024-maryland-biogeneius-finalist/",
                "https://linkedin.com/in/martin-meister-6b17a3346",
            ],
            "notes": "MIT German House supplies Class of 2029; a public profile jointly links MIT, Centennial High School, and the same graduation dates used by the competition sources.",
        },
        {
            "record_type": "mit_student",
            "person_name": "Grace Lin",
            "mit_status": "current_undergrad",
            "mit_class_year": 2028,
            "mit_evidence_url": "https://cs3.mit.edu/news-media/news-outreach/high-school-student-co-authors-mit-joint-program-journal-article",
            "high_school": "Byram Hills High School",
            "hs_grad_year": 2024,
            "activities": [
                activity(
                    "research_science_fair",
                    "behavioral and social sciences — WESEF",
                    "regional",
                    "Won first place in Behavioral and Social Sciences at the 2024 Regeneron Westchester Science and Engineering Fair.",
                    "https://cs3.mit.edu/news-media/news-outreach/high-school-student-co-authors-mit-joint-program-journal-article",
                ),
                activity(
                    "research_science_fair",
                    "environmental economics research",
                    "international",
                    "Co-authored a peer-reviewed study on the recreation-use value of U.S. natural lands while in high school.",
                    "https://cs3.mit.edu/news-media/news-outreach/high-school-student-co-authors-mit-joint-program-journal-article",
                ),
            ],
            "flagship_category": "research_science_fair",
            "flagship_signal": "2024 Regeneron WESEF first place and peer-reviewed environmental-economics research.",
            "flagship_confidence": "high",
            "debate": "no_documented",
            "debate_details": None,
            "source_urls": [
                "https://cs3.mit.edu/news-media/news-outreach/high-school-student-co-authors-mit-joint-program-journal-article"
            ],
            "notes": "A single MIT-hosted article jointly identifies Lin, Byram Hills, the award, and matriculation in MIT Class of 2028.",
        },
        {
            "record_type": "mit_student",
            "person_name": "Ishana Chadha",
            "mit_status": "current_undergrad",
            "mit_class_year": 2029,
            "mit_evidence_url": "https://axo.mit.edu/sisters/",
            "high_school": "Commack High School",
            "hs_grad_year": 2025,
            "activities": [
                activity(
                    "research_science_fair",
                    "neuroscience — Regeneron STS",
                    "national",
                    "Named a 2025 Regeneron STS finalist for research on genes regulating pyramidal-neuron migration during brain development.",
                    "https://www.societyforscience.org/regeneron-sts/2025-student-finalists/ishana-chadha/",
                ),
                activity(
                    "debate_speech",
                    "school debate and forensics",
                    "regional",
                    "Founded Commack's debate club and earned individual and team awards in the Long Island Forensics Association.",
                    "https://www.societyforscience.org/regeneron-sts/2025-student-finalists/ishana-chadha/",
                ),
                activity(
                    "community_civic",
                    "STEAM outreach",
                    "regional",
                    "Created and organized K-12 STEAM projects for Bake Back America.",
                    "https://www.societyforscience.org/regeneron-sts/2025-student-finalists/ishana-chadha/",
                ),
            ],
            "flagship_category": "research_science_fair",
            "flagship_signal": "2025 Regeneron STS finalist in neuroscience.",
            "flagship_confidence": "high",
            "debate": "yes",
            "debate_details": "Founded Commack High School's debate club and competed in Long Island forensics.",
            "source_urls": [
                "https://axo.mit.edu/sisters/",
                "https://www.societyforscience.org/regeneron-sts/2025-student-finalists/ishana-chadha/",
            ],
            "notes": "MIT Alpha Chi Omega lists Chadha in Class of 2029; the official STS profile supplies school and exact identity context.",
        },
        {
            "record_type": "mit_student",
            "person_name": "Ryan Junsung Jang",
            "mit_status": "current_undergrad",
            "mit_class_year": 2028,
            "mit_evidence_url": clubchem,
            "high_school": "Seoul Science High School",
            "hs_grad_year": 2024,
            "activities": [
                activity(
                    "academic_olympiad",
                    "chemistry — International Chemistry Olympiad",
                    "international",
                    "Won a gold medal for South Korea at the 2023 International Chemistry Olympiad, ranking 30th.",
                    "https://www.icho-official.org/results/results.php?id=55&year=2023",
                )
            ],
            "flagship_category": "academic_olympiad",
            "flagship_signal": "2023 International Chemistry Olympiad gold medalist.",
            "flagship_confidence": "medium",
            "debate": "no_documented",
            "debate_details": None,
            "source_urls": [
                clubchem,
                "https://www.icho-official.org/results/results.php?id=55&year=2023",
                "https://www.dongascience.com/en/news/60874",
            ],
            "notes": "MIT ClubChem jointly lists Ryan Jang '28 as a chemistry and biology major from South Korea; IChO and Korean reporting identify Junsung Jang of Seoul Science High School.",
        },
        {
            "record_type": "mit_student",
            "person_name": "Bergüzar Yürüm",
            "mit_status": "current_undergrad",
            "mit_class_year": 2029,
            "mit_evidence_url": "https://dh.mit.edu/home/",
            "high_school": "Osman Ulubaş Kayseri Science High School",
            "hs_grad_year": 2025,
            "activities": [
                activity(
                    "academic_olympiad",
                    "informatics — European Girls' Olympiad in Informatics",
                    "international",
                    "Won the gold medal and placed second overall at the 2024 European Girls' Olympiad in Informatics.",
                    "https://stats.egoi.org/editions/2024/results/",
                ),
                activity(
                    "academic_olympiad",
                    "informatics — European Girls' Olympiad in Informatics",
                    "international",
                    "Won a silver medal at the 2023 European Girls' Olympiad in Informatics.",
                    "https://stats.egoi.org/editions/2023/results/",
                ),
            ],
            "flagship_category": "academic_olympiad",
            "flagship_signal": "2024 European Girls' Olympiad in Informatics gold medalist and overall runner-up.",
            "flagship_confidence": "high",
            "debate": "no_documented",
            "debate_details": None,
            "source_urls": [
                "https://dh.mit.edu/home/",
                "https://stats.egoi.org/editions/2024/results/",
                "https://stats.egoi.org/editions/2023/results/",
                "https://www.kayseriolay.com/kayseri-nin-gururu-berguzar-yurum-avrupa-dan-altin-madalya-ile-dondu/133199/",
            ],
            "notes": "MIT German House lists Yürüm in Class of 2029; the uncommon full name and Turkish school/country context match the official EGOI results.",
        },
        {
            "record_type": "mit_student",
            "person_name": "Anthony Lin",
            "mit_status": "current_undergrad",
            "mit_class_year": 2028,
            "mit_evidence_url": clubchem,
            "high_school": "The Bronx High School of Science",
            "hs_grad_year": 2024,
            "activities": [
                activity(
                    "academic_olympiad",
                    "Science Olympiad — chemistry, engineering, and forensics",
                    "state",
                    "Won second place in Chemistry Lab and additional top-ten medals in Air Trajectory and Forensics at the 2024 New York State Science Olympiad tournament.",
                    "https://www.bxscience.edu/apps/news/show_news.jsp?REC_ID=903410&id=1",
                ),
                activity(
                    "academic_olympiad",
                    "Science Olympiad — regional tournament",
                    "regional",
                    "Won first place in Chemistry Lab, Flight, Forensics, and Robot Tour at the 2024 NYC North Science Olympiad regional tournament.",
                    "https://www.bxscience.edu/apps/news/show_news.jsp?REC_ID=894607&id=1",
                ),
                activity(
                    "research_science_fair",
                    "earth and environmental sciences — Regeneron ISEF",
                    "international",
                    "Won second place in Earth and Environmental Sciences and a NASA Earth System Science Award at Regeneron ISEF 2023.",
                    "https://bxscience.edu/apps/news/show_news.jsp?REC_ID=846640&id=1",
                ),
            ],
            "flagship_category": "academic_olympiad",
            "flagship_signal": "Multiple 2024 New York Science Olympiad medals, including state second place in Chemistry Lab.",
            "flagship_confidence": "medium",
            "debate": "no_documented",
            "debate_details": None,
            "source_urls": [
                clubchem,
                "https://www.bxscience.edu/apps/news/show_news.jsp?REC_ID=903410&id=1",
                "https://www.bxscience.edu/apps/news/show_news.jsp?REC_ID=894607&id=1",
                "https://bxscience.edu/apps/news/show_news.jsp?REC_ID=846640&id=1",
            ],
            "notes": "MIT ClubChem lists Anthony Lin '28 from NYC; Bronx Science lists Anthony Lin '24 in chemistry-centered Science Olympiad and ISEF activities, providing aligned geography, cohort, and subject context.",
        },
    ]


def load_existing_names():
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        return {
            normalize_name(row.get("person_name"))
            for row in csv.DictReader(handle)
            if row.get("person_name")
        }


def record_score(record):
    confidence = {"high": 3, "medium": 2, "low": 1}.get(
        record.get("flagship_confidence"), 0
    )
    category = {
        "academic_olympiad": 5,
        "research_science_fair": 5,
        "robotics_engineering": 4,
        "cs_projects_competitions": 4,
        "maker_building": 3,
    }.get(record.get("flagship_category"), 0)
    level = max(
        (
            {
                "international": 6,
                "national": 5,
                "state": 4,
                "regional": 3,
                "school": 2,
                "participation": 1,
                "unknown": 0,
            }.get(item.get("level"), 0)
            for item in record.get("activities", [])
        ),
        default=0,
    )
    return confidence, category, level


def merge_record(current, incoming):
    if current is None:
        return incoming

    if record_score(incoming) > record_score(current):
        base, other = incoming, current
    else:
        base, other = current, incoming

    merged = dict(base)
    if not merged.get("high_school") and other.get("high_school"):
        merged["high_school"] = other["high_school"]
    if not merged.get("hs_grad_year") and other.get("hs_grad_year"):
        merged["hs_grad_year"] = other["hs_grad_year"]

    seen_activities = set()
    activities = []
    for item in current.get("activities", []) + incoming.get("activities", []):
        key = (
            item.get("category"),
            item.get("subcategory"),
            item.get("achievement"),
            item.get("evidence_url"),
        )
        if key not in seen_activities:
            seen_activities.add(key)
            activities.append(item)
    merged["activities"] = activities

    source_urls = []
    for url in current.get("source_urls", []) + incoming.get("source_urls", []):
        if url and url not in source_urls:
            source_urls.append(url)
    merged["source_urls"] = source_urls

    notes = []
    for text in (current.get("notes"), incoming.get("notes")):
        if text and text not in notes:
            notes.append(text)
    merged["notes"] = " | ".join(notes)
    if current.get("debate") == "yes" or incoming.get("debate") == "yes":
        merged["debate"] = "yes"
        merged["debate_details"] = (
            current.get("debate_details") or incoming.get("debate_details")
        )
    return merged


def validate_record(record):
    required = {
        "record_type",
        "person_name",
        "mit_status",
        "mit_class_year",
        "mit_evidence_url",
        "high_school",
        "hs_grad_year",
        "activities",
        "flagship_category",
        "flagship_signal",
        "flagship_confidence",
        "debate",
        "debate_details",
        "source_urls",
        "notes",
    }
    missing = required.difference(record)
    if missing:
        raise ValueError(f"{record.get('person_name')}: missing fields {sorted(missing)}")
    if record["record_type"] != "mit_student":
        raise ValueError(f"{record['person_name']}: wrong record_type")
    if record["mit_class_year"] not in {2028, 2029}:
        raise ValueError(f"{record['person_name']}: invalid class year")
    if record["flagship_category"] not in ALLOWED_CATEGORIES | {"unknown"}:
        raise ValueError(f"{record['person_name']}: invalid flagship category")
    if record["flagship_confidence"] not in {"high", "medium", "low"}:
        raise ValueError(f"{record['person_name']}: invalid confidence")
    if record["debate"] not in {"yes", "no_documented", "unknown"}:
        raise ValueError(f"{record['person_name']}: invalid debate value")
    if not urlparse(record["mit_evidence_url"]).scheme:
        raise ValueError(f"{record['person_name']}: invalid MIT evidence URL")
    if not record["activities"]:
        raise ValueError(f"{record['person_name']}: no cross-match activity")
    for item in record["activities"]:
        if item.get("category") not in ALLOWED_CATEGORIES:
            raise ValueError(
                f"{record['person_name']}: invalid activity category {item.get('category')}"
            )
        if not item.get("evidence_url"):
            raise ValueError(f"{record['person_name']}: activity lacks evidence URL")


def apply_targeted_corrections(record):
    name = record["person_name"]
    if name == "Ben Wu":
        for item in record["activities"]:
            if "AIME" in item.get("achievement", ""):
                item["achievement"] = (
                    "Qualified for the American Invitational Mathematics Examination "
                    "in February 2023."
                )
                item["evidence_url"] = "https://linkedin.com/in/bwu142"
        record["flagship_category"] = "academic_olympiad"
        record["flagship_signal"] = "2023 AIME qualifier."
        record["source_urls"].append("https://linkedin.com/in/bwu142")
    elif name == "Brian Li":
        for item in record["activities"]:
            if "PRIMES" in item.get("achievement", ""):
                item["achievement"] = (
                    "Conducted 2023-2024 PRIMES-USA research on Whittaker vectors "
                    "and non-standard quantizations, presenting at the PRIMES "
                    "conference and 2024 Joint Mathematics Meetings."
                )
    elif name == "Emily Alemán":
        for item in record["activities"]:
            if "ISEF" in item.get("achievement", ""):
                item["achievement"] = (
                    "Won second place in Physics and Astronomy at 2024 ISEF, a NASA "
                    "special award, and first place in physical sciences at JSHS."
                )
    elif name == "Fiona Wang":
        record["activities"].append(
            activity(
                "robotics_engineering",
                "FIRST Tech Challenge",
                "national",
                "Named a FIRST Tech Challenge Dean's List Finalist in 2023.",
                "https://linkedin.com/in/fiona-wang-40b16818b",
            )
        )
        record["source_urls"].append(
            "https://linkedin.com/in/fiona-wang-40b16818b"
        )
    elif name == "Kelsey Morey":
        for item in record["activities"]:
            if "Math Prize for Girls" in item.get("achievement", ""):
                item["achievement"] = (
                    "Placed among the top 35 scorers in the 2023 Math Prize for Girls "
                    "and advanced to its Olympiad round."
                )
        record["flagship_signal"] = (
            "Top-35 scorer and Olympiad-round qualifier at the 2023 Math Prize for Girls."
        )
    elif name == "Melat Ghebreselassie":
        for item in record["activities"]:
            if "Seed.link" in item.get("achievement", ""):
                item["achievement"] = (
                    "Helped build Seed.link, a soil-sensing and machine-learning device; "
                    "the team won first place in the 2024 MESA National Engineering "
                    "Design Competition poster symposium."
                )
                item["evidence_url"] = (
                    "https://mocoshow.com/2024/08/24/"
                    "springbrook-hs-students-win-award-in-national-engineering-contest/"
                )
        record["source_urls"].append(
            "https://mocoshow.com/2024/08/24/"
            "springbrook-hs-students-win-award-in-national-engineering-contest/"
        )
    elif name == "Paddy Garman":
        record["activities"].append(
            activity(
                "academic_olympiad",
                "physics — PhysicsBowl",
                "international",
                "Appeared among the top 100 Division 1 global scores in the 2023 PhysicsBowl.",
                "https://aapt.org/Programs/PhysicsBowl/upload/2023-Global-Top-Scores.pdf",
            )
        )
        record["source_urls"].append(
            "https://aapt.org/Programs/PhysicsBowl/upload/2023-Global-Top-Scores.pdf"
        )
    elif name == "Ruiyang (Raymond) Luo":
        for item in record["activities"]:
            if "PRIMES" in item.get("achievement", ""):
                item["achievement"] = (
                    "Studied cyclic base orderings of matroids through PRIMES-USA "
                    "and presented the work at the 2023 PRIMES conference."
                )
    elif name == "Sam Lizotte":
        for item in record["activities"]:
            if "Massachusetts" in item.get("achievement", ""):
                item["achievement"] = (
                    "Placed second at the 2024 Massachusetts Region V Science Fair, "
                    "earned a Massachusetts Life Sciences award, and received state "
                    "fair honorable mention for an Alzheimer's-diagnosis ML project."
                )
    elif name == "Alexia Ninios":
        record["flagship_category"] = "academic_olympiad"
        record["flagship_signal"] = (
            "2024 UK Biology Olympiad silver and 2023 UK Girls' Mathematical "
            "Olympiad merit."
        )
    elif name == "Fidan Huseynova":
        record["flagship_category"] = "academic_olympiad"
        record["flagship_signal"] = (
            "2023 European Girls' Olympiad in Informatics gold medalist."
        )
    elif name == "Milon Kalia":
        record["flagship_category"] = "academic_olympiad"
        record["flagship_signal"] = (
            "Qualified for the 2023 and 2024 British Mathematical Olympiad."
        )
    record["source_urls"] = list(dict.fromkeys(record["source_urls"]))
    return record


def main():
    existing_names = load_existing_names()
    records = {}

    for filename, selected_names in SELECTIONS.items():
        path = ROOT / filename
        with path.open("r", encoding="utf-8-sig") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("person_name") not in selected_names:
                    continue
                key = normalize_name(record["person_name"])
                if key in existing_names:
                    continue
                override = MIT_EVIDENCE_OVERRIDES.get(record["person_name"])
                if override:
                    record["mit_evidence_url"] = override
                    record.setdefault("source_urls", [])
                    if override not in record["source_urls"]:
                        record["source_urls"].insert(0, override)
                    note_parts = [
                        part.strip()
                        for part in record.get("notes", "").split("|")
                        if not re.search(
                            r"class year mapped|mapped from|maps to Class|inferred from",
                            part,
                            flags=re.IGNORECASE,
                        )
                    ]
                    note_parts.append(
                        f"Explicit MIT class-year source: {override}."
                    )
                    record["notes"] = " | ".join(note_parts)
                source_note = f"Cross-match source record: {filename}:{line_number}."
                record["notes"] = (
                    f"{record.get('notes', '').strip()} | {source_note}".strip(" |")
                )
                records[key] = merge_record(records.get(key), record)

    for record in supplemental_records():
        key = normalize_name(record["person_name"])
        if key in existing_names:
            continue
        records[key] = merge_record(records.get(key), record)

    records = {
        key: apply_targeted_corrections(record)
        for key, record in records.items()
        if record["person_name"] in QUALIFYING_NAMES
    }

    ordered = sorted(
        records.values(),
        key=lambda item: (item["mit_class_year"], normalize_name(item["person_name"])),
    )
    output_names = [normalize_name(record["person_name"]) for record in ordered]
    if len(output_names) != len(set(output_names)):
        raise ValueError("Duplicate normalized names in output")
    overlap = set(output_names).intersection(existing_names)
    if overlap:
        raise ValueError(f"Output overlaps mit_students.csv: {sorted(overlap)}")
    for record in ordered:
        validate_record(record)

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        for record in ordered:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")

    print(json.dumps({"output": str(OUTPUT_PATH), "rows": len(ordered)}))


if __name__ == "__main__":
    main()
