# Project Idea and Planning Worksheets

This document contains the team worksheets for the accessibility-focused store access and ordering service. It is kept locally as the working project brief.
Worksheet 1: Problem Definition
College
GIST
Team Name
1등 
Service Name
(TBD)


Guideline
- Clearly define which local area, which social issue, and who the technology we are developing is needed for. - Example format: Region × Problem × Target Group × Need for Technology
[Example] Daramjwi Taxi (Yonsei University Yeonsongi Team
- Region: Okcheon-gun
- Problem: Limited mobility due to insufficient public transportation and the inconvenience of calling existing call taxis
- Target Group: Seniors with limited access to public transportation
- Need for Technology: The need for a voice-recognition-based one-touch taxi-calling app to reduce the difficulty of making phone calls and requesting rides through existing call taxi services


Key Definition Elements
Detailed Description (Fill-in Section)
Problem to Solve
(What social issue are you trying to address?
[Problems Identified During the Field Trip]
Even when using accessibility-enabled kiosks, users with disabilities may take a long time to complete an order, and some functions such as voice guidance and screen magnification may not work properly.
Users with physical disabilities may have difficulty using kiosks because of their physical height and accessibility.
Some kiosks have insufficient contrast between text and background in their UI/UX, making them difficult to use for people with low vision.

[Expanded Definition of the Problem]
Stage 1. Can the user easily access the store?
Before visiting a store, users with disabilities need to know in advance about accessibility facilities and features available at the store.
There are already many existing map-based services that provide accessibility information.
Stage 2. What ordering methods are available at the store?
Accessibility is not limited to whether a person using a wheelchair can enter a store or whether the store has tactile paving or Braille. Accessibility also needs to be considered for the ordering process after arriving at the store.
Stage 3. Can the user actually place an order without significant difficulty?
As observed during the field trip, users with disabilities currently face difficulties when placing orders using kiosks.

[Problem We Focused On]
Existing services and research related to accessibility often focus on a specific stage, such as store accessibility, navigation, or kiosk accessibility.
However, the actual user experience does not consist of these stages separately; they are continuously connected from visiting a store to completing an order.
Therefore, rather than addressing only one specific stage, we aim to connect and provide the accessibility information needed throughout the process of accessing a store, identifying available ordering methods, and placing and completing an order.
Target Area
(Where does this issue mainly occur?)
Stores and commercial facilities that use kiosks and various ordering methods
.
(Initial QA will be conducted at GIST, followed by real-world application and testing in areas such as Seongsu (Seoul), where many stores are concentrated within a relatively small area.)
Key Target Group
(Who is this technology for?)
Users who have difficulty using kiosks and accessing stores, including people who are blind or have low vision and people with physical disabilities.

(The target users may be adjusted based on future user interviews or additional research.)
Neet for IT/Technology
(What role does IT technology play in solving this problem?)
The technology is expected to provide information on whether a store is accessible, accessibility information based on the user's current location and situation after arriving at the store, and the ordering methods available at the store.
[Technologies Under Consideration]
1. GPS / Geofencing
- Set a virtual geographic boundary (geo-fence) around a store so that the user can receive a notification when approaching the store.
- Help identify whether the user has approached a specific store or building.

2. Beacon (BLE, Bluetooth Low Energy)
- Use signals between BLE beacons installed inside a store or building and the user's smartphone.
- Complement the limitations of GPS, such as difficulty with fine-grained positioning and limited information about multi-level indoor spaces.
One-sentence Definition of the Technology
Our team will solve theconnected accessibility challenges from store access to ordering
experienced by users who have difficulty using kiosks and accessing stores
at stores that use kiosks and ordering services
by connecting and providing the information needed at each stage through location-based technologies and accessibility information.





Worksheet 2: Prioritizing Features
Affiliated University


GIST
Team Name


1등
Service Name


(TBD)


Writing Guide
Feature Listing: List the core features required for the service based on the previously defined problem, target audience, and role of IT/technology.
Prioritization using MoSCoW Method: Must (essential), Should (recommended), Could (optional), Won't (excluded).
MVP Inclusion Decision (O/X): Distinguish between features that must be included in the first version (O) and features to be deferred to later versions (X).
User Story Writing: Specify the purpose and context of use in the format: "As a user, I can do [What] in order to [Why]."


Category
Detailed Feature Name
User Story (Feature Description)
MoSCoW
MVP
Remarks
Stage 1 (Store Access)
Store Accessibility Information
Users can check accessibility information relevant to their needs, such as entrances and elevators, before visiting a store.
Must
O
Consider using existing accessibility data/APIs
Stage 1 (Store Access)
GPS / Geofencing-based Store Recognition
Users can view information about a store when they approach it.
Must
O


Stage 2 (Ordering Method)
Ordering Method Information
Users can check the ordering methods currently available at a store, such as kiosks, QR codes, table ordering, or ordering from staff.
Must
O


Stage 2 (Ordering Method)
BLE-based Ordering Location Guidance
Users can identify the location they need to approach in order to place an order inside the store.
Should
X
Investigate indoor positioning technology
Stage 3 (Ordering)
Menu, Price, and Option Information
Users can check menu items, prices, and options on their smartphone.
Must
O
Investigate how to obtain actual menu data
Stage 3 (Ordering)
Voice-based Menu Selection and Ordering
Users can select menu items and options and place an order using their voice without directly operating the screen.
Should
X
Determine necessity through initial user validation








Worksheet 3: Project Schedule (WBS)
College
GIST
Team Name
1등
Service Name
(TBD)


 Writing Guide 
- Divide the process from project initiation to completion into weekly plans, and assign a person in charge for each task. 
- Please include all necessary steps to complete the project, not just development, but also planning, design, and QA (testing). 



Week
Phase
Main Tasks (To-Do)
Person in Charge
Status
Deliverables
Weeks 1–2
Team Formation & Onboarding
Form the team, understand the project and social issue, assign team roles, and discuss the overall project direction.
PM / All
Done
Team structure and role assignments
Week 3
Field Trip
Identify accessibility and ordering-related difficulties experienced by users with disabilities in real-world settings.
PM / All
Done
Field trip observations and interview notes
Weeks 4–5
Field Trip Briefing / Problem Definition
Based on the problems identified during the field trip, define the core users and problem to be addressed, and investigate existing services and solutions.
PM / All
Done
Field trip briefing PPT / Problem Definition Worksheet
Week 6
Service Planning
Define the service direction, develop the user journey and service flow, and finalize MVP features and priorities.
PM /
UI/UX / Full-Stack
Planned
Service plan, MVP feature list
Weeks 7–8
App Design & UI/UX
Refine the user flow, design an accessible UI/UX, and design key screens and user interactions.
UI/UX /
PM
Planned
User flow, UI mockups
Week 9
UI & System Design / Midterm Presentation
Finalize the UI design, select the technology stack, review data/API usage, design the system architecture, and prepare for and deliver the midterm presentation. (Midterm Presentation: Oct. 29 (Thu))
UI/UX / Front-end / Back-end / Full-Stack
Planned
Final UI mockups, system architecture diagram / Midterm presentation PPT
Week 10
Core Feature Development
Implement store accessibility information and store recognition features, and develop the ordering method information feature.
Front-end / Back-end / Full-Stack
Planned
Initial functional prototype
Week 11
Ordering-related Feature Development
Implement menu, price, and option information, and investigate the feasibility of BLE for ordering location guidance and develop a prototype.
Front-end / Back-end / Full-Stack
Planned
Ordering- related functional prototype,
BLE prototype
Week 12
Service Integration
Integrate the main features into a single service flow and connect the data/APIs and individual functions.
Front-end / Back-end / Full-Stack
Planned
Integrated prototype
Week 13
Integration Testing (QA)
Test the overall user flow and key features, verify accessibility and errors, and fix identified issues.
QA / All
Planned
Test results and improvement list, beta version
Week 14
User Testing & Improvement
Validate usability with actual or test users, measure the ordering process and time required, and incorporate feedback.
QA /
UI/UX /
PM / All
Planned
User testing results, improved final MVP
Week 15
Final Presentation
Summarize the project progress and prepare for and deliver the final presentation. (Final Presentation: Dec. 10 (Thu))
PM / All
Planned
Final presentation PPT / Final completed service
