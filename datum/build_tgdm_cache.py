"""
One-off script: builds data/tgdm/tgdm_index.json directly from the TGD M 2022
text supplied to this session, bypassing PDF text-extraction entirely.

review/tgdm_index.py's load_index() reads this cache whenever it is newer
than (or the only thing available in place of) data/tgdm/TGD-M.pdf, so the
review pipeline works against real, verbatim clause text without needing the
literal PDF file on disk.

Run once: python build_tgdm_cache.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "tgdm" / "tgdm_index.json"

SCOPE = {
    "0": "Part M — general application",
    "1": "Section 1 — buildings other than dwellings",
    "2": "Section 2 — existing buildings other than dwellings",
    "3": "Section 3 — dwellings",
}


def c(clause_id, heading, page, text):
    return {
        "clause_id": clause_id,
        "heading": heading,
        "text": " ".join(text.split()),
        "page": page,
        "scope": SCOPE[clause_id[0]],
    }


CLAUSES = [

# ---------------------------------------------------------------------
# Part M — The Requirement
# ---------------------------------------------------------------------
c("0.1", "General", 6,
  "Part M aims to foster an inclusive approach to the design and construction of the built environment. "
  "The requirements of Part M (M1-M5) aim to ensure that regardless of age, size or disability: new buildings "
  "other than dwellings are accessible and usable; extensions to existing buildings other than dwellings are, "
  "where practicable, accessible and usable; material alterations to existing buildings other than dwellings "
  "increase accessibility and usability where practicable; certain changes of use increase accessibility where "
  "practicable; and new dwellings are visitable. In doing so the Requirements underpin the principle of "
  "Universal Design, defined in the Disability Act 2005 as the design and composition of an environment so that "
  "it may be accessed, understood and used to the greatest practicable extent, in the most independent and "
  "natural manner possible, in the widest possible range of situations and without the need for adaptation, "
  "modification, assistive devices or specialised solutions, by persons of any age or size or having any "
  "particular physical, sensory, mental health or intellectual ability or disability. This document, TGD M, "
  "sets out guidance on the minimum level of provision to meet requirements M1-M5."),

c("0.2", "The Requirements", 7,
  "In order to satisfy the requirements of Part M, all buildings should be designed and constructed so that: "
  "(a) people can safely and independently approach, gain access and use a building, its facilities and its "
  "environs, and (b) elements of the building do not constitute an undue hazard for people, especially for "
  "people with vision, hearing or mobility impairments."),

c("0.3", "Buildings Other than Dwellings", 7,
  "In the case of buildings other than dwellings, the building should also be designed and constructed so that: "
  "(a) people can circulate within the building and use the building's facilities; (b) where sanitary facilities "
  "are provided, adequate sanitary facilities are available and accessible to people with a range of abilities, "
  "and where sanitary facilities are provided in a building, or in a building that is to be extended, adequate "
  "provision shall be made for people to access and use a changing places toilet, having regard to the use and "
  "size of the building; (c) where relevant facilities such as fixed/unfixed seating for audience or spectators, "
  "refreshment facilities, sleeping accommodation and the like are provided, adequate provision is made for "
  "people with a range of abilities; (d) suitable aids to communication are available for people with vision, "
  "hearing or mobility impairments. A 'changing places toilet' means an accessible sanitary facility with a "
  "toilet, hoist, basin, adult-sized changing bench and optional shower, with adequate space for use by persons "
  "with a range of abilities who may require assistance."),

c("0.4", "Dwellings", 8,
  "Dwellings should be designed and constructed so that: (a) people can safely and conveniently approach and "
  "gain access — where due to site specific constraints or where all entrances are on other than ground level "
  "and a suitable passenger lift is not provided, it is considered adequate to provide access by means of steps, "
  "or a stairway suitable for use by ambulant disabled people; (b) people can have access to the main habitable "
  "rooms at entry level — where there is no habitable room at this level, it is considered adequate to provide "
  "for access to habitable rooms on the storey containing the main living room, and access to this storey from "
  "the entry storey may be by means of a stairway suitable for use by ambulant disabled people; (c) a WC is "
  "provided at entry level or, where there are no habitable rooms at this level, on the storey containing the "
  "main living room."),

c("0.5", "Use of the Guidance", 8,
  "TGD M 2022 is divided into 3 sections. Section 1 sets out the minimum level of provision for buildings other "
  "than dwellings and their environs, and the common areas of apartment blocks and their environs, to meet the "
  "requirements of M1 to M4. Section 1 applies to both new and existing buildings. Section 2 should be read in "
  "conjunction with Section 1 and provides additional guidance for existing buildings other than dwellings and "
  "the common areas of existing apartment blocks, on the minimum provisions for certain elements and features "
  "where it is not practicable to achieve the provisions set out in Section 1. Section 3 applies to dwellings "
  "and their environs, including individual dwelling houses and individual apartments; it does not apply to the "
  "common areas of apartment blocks, but does apply to the common areas of duplex buildings."),

c("0.6", "Application of Part M", 9,
  "The Requirements of Part M apply to: (a) works in connection with new buildings and new dwellings, including "
  "the changing places toilet requirement (M4) where sanitary facilities are provided, having regard to the use "
  "and size of the building (Table 1); (b) works in connection with extensions to existing buildings — under M2 "
  "adequate provision must be made to approach and access an extension, by an adequate independent approach and "
  "entrance or, where not practicable, by modifying the existing approach and entrance where practicable; under "
  "M3, where sanitary facilities are provided in a building, adequate accessible sanitary facilities must be "
  "provided for people using the extension; under M4 a changing places toilet may be required having regard to "
  "use and size; (c) works in connection with material alterations of existing buildings — alterations to "
  "features relevant to compliance with Part M (entrances, circulation, etc.) must comply with M1, and the "
  "building as a whole (including the approach from the site boundary and from on-site car parking where "
  "provided) must be no less compliant with M1 following the alteration, though it is not necessary to upgrade "
  "existing access to the entrance unless the entrance itself is materially altered; (d) an existing building or "
  "part of it which undergoes a material change of use to a day centre, hotel, hostel or guest building, "
  "institutional building, place of assembly, shop (not ancillary) or shopping centre — where the change of use "
  "applies to the whole building it must comply with M1 to M4; where it applies only to part of the building, "
  "that part must comply with M1 and M4, and the approach/access to that part, where practicable, must comply "
  "with M1, and any sanitary facility in or connected with it must comply with M1 and M4; (e) Part M does NOT "
  "apply to works in connection with extensions to and material alterations of existing dwellings, provided such "
  "works do not create a new dwelling — however an extension or material alteration of a dwelling must not make "
  "the dwelling, as a whole, less satisfactory in relation to Part M than it was before; (f) Part M does not "
  "apply to parts of a building used solely to enable inspection, repair or maintenance; (g) the provision of a "
  "changing places toilet is related to the use and size of the building — Table 1 sets out the relevant "
  "building uses and size criteria (e.g. hospital >500 m2; day centre >500 m2; places of assembly >1,000 m2 or "
  "leisure facility >500 m2 with a pool >10 m; school >1,000 m2; office with gross floor area >20,000 m2 or a "
  "public-body office >250 m2 with public sanitary facilities; shop >2,500 m2; shopping centre/retail park "
  ">5,000 m2; hotel with gross floor area >8,000 m2 or leisure/conference facilities meeting stated thresholds; "
  "public sanitary facilities buildings providing two or more WCs; outdoor amenity buildings serving more than "
  "2,000 people). For extensions, at least one changing places toilet should be provided when the combined floor "
  "area after extension exceeds the new-building threshold and the extension itself exceeds 25% of that "
  "threshold area. For material changes of use, at least one changing places toilet should be provided when the "
  "post-change floor area exceeds the equivalent new-building threshold and sanitary facilities for use by "
  "people other than staff are provided."),

c("0.7", "Determination of Practicability", 19,
  "In determining 'practicability' with respect to works to an existing building, its facilities or its "
  "environs, the following non-exhaustive circumstances should be considered: (a) where the works would have a "
  "significant adverse effect on the historical significance of the existing building, facility or environs, "
  "e.g. works to a Protected Structure; (b) where existing structural conditions would require moving or "
  "altering a load-bearing member essential to overall structural stability; (c) where other existing physical "
  "or site constraints would prohibit modification of an existing feature; (d) where works would need to be "
  "carried out on part of a building not under the same control/ownership, e.g. a sub-leaseholder in a "
  "multi-occupancy building; (e) where specific alternative guidance to Section 1 is provided in Section 2 and "
  "an existing feature or facility satisfies that guidance; (f) where a specific planning condition prohibits "
  "modification of an identified existing feature."),

c("0.8", "Existing Buildings", 20,
  "Building Regulations do not apply to buildings subject to the National Monuments Acts 1930 to 2004. Where "
  "works to existing buildings are carried out in accordance with Section 1, this will, prima facie, indicate "
  "compliance with Part M; where it is not practicable to apply Section 1 and works are carried out to Section "
  "2 instead, this will also prima facie indicate compliance. The adoption without modification of the guidance "
  "may not always be appropriate, particularly for buildings of architectural or historical interest; liaison "
  "with the local Building Control Authority on alternative approaches, or a dispensation or relaxation of the "
  "Requirements, may be considered."),

c("0.9", "Fire Safety", 21,
  "Access provision must be linked to provision for emergency egress in the case of a fire. The scope of Part M "
  "is limited to matters of access to and use of a building; for guidance on means of escape or evacuation, "
  "reference should be made to Technical Guidance Document B (Fire Safety) and the NDA publication 'Safe "
  "Evacuation for All'."),

c("0.10", "Diagrams", 22,
  "Diagrams in this document are intended to clarify aspects of the guidance; they are not necessarily to scale "
  "and do not represent fully detailed solutions. Where dimensions are stated they refer to minimum or a range "
  "of finished dimensions, and allowance should be made for tolerances, finishes and on-site deviation."),

c("0.11", "Disability Act 2005", 22,
  "The Disability Act 2005 requires public bodies to make their public buildings comply with Part M 2000 by "
  "2015 and Part M 2010 by 2022, and requires public buildings be brought into compliance with amendments to "
  "Part M not later than 10 years after commencement of the amendment. 'Public building' means a building, or "
  "part of a building, to which members of the public generally have access and which is occupied, managed or "
  "controlled by a public body."),

c("0.12", "Management", 22,
  "Whilst the provisions of the Building Regulations do not relate to management or maintenance, these "
  "functions contribute to the ongoing accessibility of a building. Key management issues include: arranging "
  "furniture appropriately; keeping circulation routes clear and facilities clean and functioning; carrying out "
  "maintenance audits regularly; staff training and awareness on assistive equipment; a detailed emergency "
  "action plan for safe egress for all; procurement of accessible goods and services; and providing pre-visit "
  "accessibility information."),

# ---------------------------------------------------------------------
# Section 1 — Access and Use of Buildings Other than Dwellings
# ---------------------------------------------------------------------
c("1.1.1", "Objective", 25,
  "The objective is to provide independently accessible means of approach to the accessible entrance(s) of a "
  "building and means of circulation around a building."),

c("1.1.2", "Introduction", 25,
  "The approach route(s) to the accessible entrance(s) of a building are the routes from the adjacent road or "
  "site-boundary entrance point, and from any designated car-parking spaces or setting-down areas. Level access "
  "routes (gradient 1:50 or less steep) accommodate the widest range of abilities and should be provided; where "
  "not possible, a gently sloped route (steeper than 1:50 but less steep than 1:20, preferably 1:20 or less "
  "steep) should be used; where not possible, a ramped route (1:20 or steeper) should be provided, with a "
  "stepped route in addition where the ramp rise exceeds 300 mm. Designated car-parking spaces (for holders of a "
  "disabled person's parking permit) should be provided on a proportional basis, and a setting-down area should "
  "be provided at or adjacent to at least one accessible entrance where there is an on-site road."),

c("1.1.3.1", "Access Routes — General", 27,
  "Projecting features that may present hazards should be avoided; where unavoidable, hazard protection "
  "(guarding/cane detection) is required if an object projects more than 100 mm into the route with its lower "
  "edge more than 300 mm above ground. Minimum unobstructed headroom is 2100 mm. Street furniture and bollards "
  "should be outside the route; bollards should be at least 1000 mm high, contrast visually, and not be linked "
  "by chains. The route should be clearly identifiable and well lit — minimum illuminance 20 lux on level/gently "
  "sloped routes, 100 lux on ramps or steps. Drainage gratings should be positioned beyond the route or flush "
  "with the surface. Dished channels should be avoided. The surface should be firm, reasonably smooth, durable "
  "and slip resistant."),

c("1.1.3.2", "Level Access Routes", 30,
  "A gradient of 1:50 or less steep is level. Minimum clear width (between walls, upstands or kerbs) should be "
  "1500 mm. Passing places for wheelchair users, 2000 mm long by 1800 mm wide, should be provided within direct "
  "sight of another or at a maximum spacing of 25 m, unless the route is at least 1800 mm wide throughout."),

c("1.1.3.3", "Gently Sloped Access Routes", 30,
  "A gradient steeper than 1:50 but less steep than 1:20 is gently sloped. Minimum clear width 1500 mm, with the "
  "same passing-place provision as level routes (not required if the route is at least 1800 mm wide or less "
  "than 25 m long). Level landings (1800 mm x 1800 mm at top/bottom, 1500 mm long intermediate landings, or 1800 "
  "x 1800 mm where sightlines are broken or three-plus flights) should be provided at each rise of 500 mm."),

c("1.1.3.4", "Ramped Access Routes", 31,
  "A gradient of 1:20 or steeper is a ramp; the preferred maximum gradient is 1:20, but ramps not steeper than "
  "1:12 may be used if individual flights are not longer than 2000 mm. Ramp gradient/length limits: going up to "
  "10 m at 1:20 (max rise 500 mm); up to 5 m at 1:15 (max rise 333 mm); up to 2 m at 1:12 (max rise 166 mm), "
  "interpolating between these. Minimum clear width 1500 mm, minimum unobstructed width between handrails 1200 "
  "mm, handrails on both sides. Top/bottom landings at least 1800 mm x 1800 mm; intermediate landings at least "
  "1500 mm long (1800 x 1800 mm as passing places where required). A 100 mm minimum upstand edge protection is "
  "required on the open side. A stepped route must be added where ramp rise exceeds 300 mm, and a platform lift "
  "alternative should be provided where the ramp is 1:20 or steeper and the total rise exceeds 2000 mm."),

c("1.1.3.5", "Stepped Access Routes", 35,
  "Minimum clear width between enclosing walls/strings/upstands is 1200 mm. Landings at top and bottom of each "
  "flight, level, at least 1200 mm long. Tactile (corduroy) hazard warning surfaces at top and bottom landings. "
  "No single steps. Rise of a flight between landings should not exceed 1500 mm (a single flight of 18 risers or "
  "fewer is acceptable if the going is 350 mm or more). Step nosings should carry a permanently contrasting "
  "strip 50-65 mm wide; projecting/overhanging nosings should be avoided. Rise of each step between 150 mm and "
  "180 mm; going of each step between 300 mm and 450 mm. Tapered treads and open risers should not be used. "
  "Continuous handrails on both sides, minimum unobstructed width between handrails not less than 1000 mm."),

c("1.1.3.6", "Handrails", 40,
  "Vertical height to the top of the upper handrail: 900-1000 mm above the pitch line of a flight, 900-1100 mm "
  "above a landing surface. A lower handrail (600-700 mm) may be added for children/short stature. Handrails "
  "should be continuous across flights and landings except where broken by side access. Where not continuous, "
  "the handrail should extend at least 300 mm beyond top/bottom and terminate in a closed end. Profile should be "
  "circular (40-50 mm diameter) or oval (50 mm wide). Clearance to any adjacent wall surface should be 50-60 mm."),

c("1.1.4", "Pedestrian Crossings", 43,
  "Where pedestrian crossings are provided, tactile paving and dropped kerbs should be provided at controlled "
  "and uncontrolled crossings in accordance with 'Good Practice Guidelines on Accessibility of Streetscapes'."),

c("1.1.5", "On–Site Car Parking", 43,
  "Designated car parking spaces are those exclusively for holders of a disabled person's parking permit. In "
  "the absence of a Local Authority requirement, at least 5% of total spaces should be designated, with a "
  "minimum provision of at least one such space. Designated bays require a 1200 mm wide access zone on both "
  "sides and the rear, clear of vehicular circulation, and should be clearly marked with the symbol of access, "
  "on firm level ground, located closest to the accessible entrance."),

c("1.1.6", "On–Site Setting Down Areas", 46,
  "Where there is an on-site road leading to the building, a setting down area should be provided at or "
  "adjacent to at least one accessible entrance, on firm and level ground as close as practicable, with an "
  "access route leading to the accessible entrance."),

c("1.2.1", "Access to Buildings — Objective", 48,
  "The objective is to provide entrances to buildings that are independently accessible and to avoid "
  "segregation based on a person's level of ability."),

c("1.2.2", "Access to Buildings — Introduction", 48,
  "All of the following entrances should be accessible: the main entrance a visitor unfamiliar with the "
  "building would normally approach; the entrance closest to the designated parking area; the entrance closest "
  "to the setting down area; any main entrance to a unique functional area of a multi-occupancy or "
  "multi-functional building; any entrance used exclusively by staff; and building exits to assembly points or "
  "the site boundary. Where it is not practicable for each to be accessible (steeply sloped/restricted sites or "
  "planning requirements), an alternative accessible entrance may be provided in such circumstances only."),

c("1.2.3", "Accessible Entrances", 48,
  "A level landing at least 1800 mm x 1800 mm, clear of any door/gate swing, should be provided immediately in "
  "front of the entrance. The threshold should be level, maximum height 15 mm with chamfered/pencil-rounded "
  "edges. The entrance should be easily identified under all lighting conditions."),

c("1.2.4", "Accessible Entrance Doors", 50,
  "Any self-closing hinged or pivoted entrance door should have a controlled closing device and allow "
  "independent use; where a controlled closing device cannot close the door against external conditions without "
  "exceeding the stated opening force, a power-operated door, a low energy swing door, or a lobby/air-lock "
  "system should be used instead. Powered sliding doors are the preferred accessible entrance door type. "
  "Revolving doors are not considered accessible; a complementary accessible door must be provided immediately "
  "adjacent and available at all times. Minimum effective clear widths (Table 3): 800 mm straight-on; 800 mm at "
  "right angles from a 1500 mm route; 825 mm at right angles from a 1200 mm route; 1000 mm for external/lobby "
  "doors at entrances of buildings used by the general public and for a changing places toilet entrance door. "
  "Door handles between 800-1050 mm above floor level (900 mm preferred)."),

c("1.2.4.1", "Accessible Glass Doors", 54,
  "A frameless glass door or fully glazed door with a narrow stile should carry permanent manifestation "
  "contrasting visually with the background, in two zones 850-1000 mm and 1400-1600 mm above floor level, "
  "visible from both sides in all lighting conditions."),

c("1.2.4.2", "Accessible Manual Doors", 55,
  "Opening force measured from the leading edge should be not more than 30N from 0° to 30° open, and not more "
  "than 22.5N from 30° to 60°. There should be an unobstructed space of at least 300 mm between the leading edge "
  "of a single-leaf door (opening towards the user) and a return wall, unless the door is opened by remote "
  "automatic control. Door opening furniture should be operable with one hand using a closed fist (e.g. a lever "
  "handle) and should contrast visually with the door surface."),

c("1.2.4.3", "Accessible Power-Operated Doors", 56,
  "Power-operated doors (sliding, swinging or folding) may be manually activated (push pad, coded entry, remote "
  "control) or automatically activated (motion/proximity sensor). Manual activation controls should be located "
  "750-1000 mm above floor level and contrast visually with the surrounding background. Control systems should "
  "incorporate a safety stop and revert to manual control, or fail safe in the open position, on power failure."),

c("1.2.4.4", "Low Energy Swing Doors", 57,
  "A low energy power-operated door operator may be used on swing doors with relatively low pedestrian usage, "
  "working in manual mode or providing push-and-go/power-assisted opening; the push-and-go assist should "
  "activate when the door is pushed beyond 25 mm."),

c("1.2.5", "Entrance Lobbies", 57,
  "Entrance lobbies should provide sufficient space to enable a wheelchair user and an assistant to move clear "
  "of one door before opening the other. Lobby length/width should follow the wheelchair-and-companion (1570 mm "
  "occupied length) formula in Diagram 11. Floor mat wells should be level with the adjacent floor finish and "
  "firm."),

c("1.3.1", "Circulation — Objective", 60,
  "The objective is for people to travel horizontally and vertically within a building conveniently and without "
  "discomfort in order to make use of all relevant facilities."),

c("1.3.2", "Circulation — Introduction", 60,
  "Each storey should allow independent circulation by people with a wide range of abilities and independent "
  "access to accessible services and facilities on that storey. Passenger lifts should be provided in all "
  "multi-storey buildings, subject to limited exceptions in 1.3.4.1.1; at least one stairs suitable for ambulant "
  "disabled people should also be provided to all floors above and below the entrance level."),

c("1.3.3.1", "Reception Area in Entrance Halls", 61,
  "A clear manoeuvring space in front of a reception desk of 1200 mm deep x 1800 mm wide (with a knee recess of "
  "at least 500 mm deep) or 1400 mm deep x 2200 mm wide (no knee recess) should be provided. A low-level counter "
  "section, working surface height 760 mm maximum, at least 1800 mm long (or 900 mm where transactions are not "
  "conducted across the desk), with a knee recess at least 700 mm above floor level, should be provided in "
  "addition to a standing-height section (950-1100 mm)."),

c("1.3.3.2", "Internal Doors", 62,
  "Doors should only be provided where necessary, and self-closing devices minimised. Opening force limits and "
  "effective clear widths mirror 1.2.4 (Table 3). An unobstructed space of at least 300 mm on the pull side "
  "between the leading edge and a return wall is required (600 mm for a changing places toilet door), unless "
  "power operated or the door serves a standard hotel bedroom/ensuite, standard cubicle, storage or maintenance "
  "area. Door handles 800-1050 mm above floor level. Door leading edges likely to be held open should contrast "
  "visually with their surroundings."),

c("1.3.3.3", "Corridors and passageways", 65,
  "Unobstructed clear corridor width should be at least 1200 mm. Passing places (1800 mm wide over 1800 mm "
  "length) should be provided where the corridor is narrower than 1800 mm, at intervals of not more than 20 m, "
  "at junctions, at ends of corridors, and opposite a sliding or inward-opening door to a changing places toilet. "
  "The floor should be level (1:50 or less steep); a gently sloping section should have a level rest area at "
  "least 1800 mm long at each 500 mm rise. Doors opening onto a major access or escape route should be recessed "
  "so they don't project into the corridor. Clear unobstructed headroom of 2100 mm should be maintained."),

c("1.3.3.4", "Internal lobbies", 67,
  "Internal lobbies to wheelchair-accessible areas should comply with the entrance lobby guidance in 1.2.5."),

c("1.3.4.1", "Vertical Features — Provision", 69,
  "A passenger lift is the most accessible means of vertical circulation. Passenger lifts should be provided in "
  "all multi-storey buildings to serve all storeys above and below entry level, except: non-residential/mixed "
  "use buildings with a nett floor area per floor under 200 m2 and no floor entrance level more than 4500 mm "
  "above/below the main entrance level; apartment buildings with four or fewer dwellings per storey (other than "
  "entrance storey) and no dwelling entrance level more than 4500 mm above/below; duplex buildings with two or "
  "fewer dwellings per storey and no dwelling entrance level more than 6500 mm above/below. Where no lift is "
  "provided, the same range of services/facilities available on other levels should be made available at entry "
  "level. In addition to a lift, at least one internal stairs suitable for ambulant disabled people should be "
  "provided."),

c("1.3.4.2", "Passenger Lift Details", 70,
  "Should conform to I.S. EN 81-1/81-2/81-70. Clear unobstructed manoeuvring space at least 1800 mm x 1800 mm in "
  "front of every lift entrance door. Lift car doors power-operated horizontal sliding, minimum 800 mm clear "
  "opening, timed to stay open at least 8 seconds. Minimum lift car internal dimensions 1100 mm wide x 1400 mm "
  "deep (2000 mm x 1400 mm in public areas of public facilities with a nett floor area over 200 m2). Controls "
  "900-1200 mm (preferably 1100 mm) above car floor, at least 500 mm from a return wall; landing call buttons "
  "900-1100 mm above the landing. Tactile floor-number indicators required. A half-length mirror opposite the "
  "door (bottom edge 900-950 mm above floor) and a handrail at 900 mm should be provided."),

c("1.3.4.3", "Internal Stairs Suitable for Ambulant Disabled People", 73,
  "Minimum clear width 1200 mm. Landings at top and bottom of each flight, level, at least 1200 mm long (or the "
  "flight width if greater). No single steps. Rise of a flight between landings should not exceed 1800 mm. Step "
  "nosings should carry a contrasting strip 50-65 mm wide; projecting nosings avoided. Rise of each step 150-180 "
  "mm, going at least 300 mm. Tapered treads/open risers not used. Continuous handrails both sides, minimum "
  "unobstructed width between handrails not less than 1000 mm (divided into 1000-2000 mm channels where the "
  "overall width exceeds 2000 mm)."),

c("1.3.4.4", "Internal Ramps", 76,
  "Where a change of level within a storey is unavoidable, a gentle slope should be provided; where the change "
  "is 300 mm or more, two or more clearly-defined contrasting steps should be added to a ramp. A ramp is a "
  "gradient of 1:20 or steeper; no flight should exceed a going of 10 m or a rise of 500 mm."),

c("1.3.4.5", "Handrails (internal stairs/ramps)", 77,
  "A suitable continuous handrail should be provided on each side of flights and landings of internal stairs "
  "suitable for ambulant disabled people and ramps, complying with the external handrail guidance in 1.1.3.6."),

c("1.4.1", "Sanitary Facilities — Objective", 78,
  "The objective is to provide independently accessible sanitary facilities that meet the needs of people with "
  "a wide range of abilities."),

c("1.4.3", "General Provisions (sanitary facilities)", 78,
  "Section 1.4.3 requires accessible sanitary facilities wherever sanitary facilities are provided in a "
  "building, for customers, visitors or staff; it does not itself create a requirement to provide sanitary "
  "facilities at all. Where sanitary facilities are provided for use by people other than staff, at least one "
  "changing places toilet should be provided in the building-use categories in Table 1, having regard to use and "
  "size. Provision guidance is based on a minimum clear wheelchair turning space of 1800 mm x 1800 mm."),

c("1.4.3.1", "Provisions for Wheelchair Accessible Unisex WCs", 79,
  "Buildings with a nett floor area per floor greater than 200 m2 should provide a wheelchair accessible unisex "
  "WC with a minimum 1800 mm x 1800 mm turning space; buildings of 200 m2 or less may use a 1500 mm x 1500 mm "
  "turning space. Where there is only one WC facility in a building it should be unisex, wheelchair accessible, "
  "and include a standing-height washbasin in addition to the finger-rinse basin. Where more than one WC facility "
  "exists at different locations, at least one wheelchair accessible unisex WC should be provided at each "
  "location. Where more than one is provided, layouts should be handed (left/right transfer)."),

c("1.4.3.2", "Provisions for WC Cubicles", 80,
  "Where WC cubicles are provided in a washroom, at least one should be a cubicle for ambulant disabled people. "
  "Where four or more cubicles are provided, one should additionally be an enlarged cubicle. Where more than one "
  "enlarged cubicle is provided, layouts should be handed."),

c("1.4.3.3", "Provisions for Urinals", 81,
  "Where one or more urinals are provided, at least one should be suitable for ambulant disabled people. Where "
  "six or more are provided, at least one accessible urinal and one low wash-hand basin should be provided for "
  "wheelchair users."),

c("1.4.3.4", "Provisions for Accessible Bathrooms/Shower Rooms", 81,
  "Where an ensuite sanitary facility is provided in an accessible bedroom for independent wheelchair use, it "
  "should comply with 1.4.8; a balanced combination of ensuite bathrooms and shower rooms should be provided "
  "where more than one is provided, and where only one accessible ensuite facility is provided it should include "
  "a shower rather than a bath."),

c("1.4.3.5", "Provisions for Changing and/or Showering Facilities", 82,
  "Where communal separate-sex changing/showering facilities are provided, accessible changing/showering "
  "facilities should also be provided within them by subdividing the area. In sport facilities an individual "
  "unisex self-contained accessible showering/changing facility should be provided in addition to communal "
  "facilities."),

c("1.4.3.6", "Provisions for Changing Places Toilets", 82,
  "At least one changing places toilet should be provided in the buildings listed in Table 1 having regard to "
  "use and size, suitably located having regard to the use and operation of the building, and provided in "
  "addition to (not instead of) standard/unisex accessible WCs and other sanitary facilities."),

c("1.4.4", "Sanitary Facilities — General", 83,
  "Accessible sanitary facilities should be located in a convenient, accessible, clearly identifiable part of "
  "the building. Taps should be lever-operated or automatic. Doors should have light-action privacy bolts and an "
  "emergency release mechanism; the fire alarm and any emergency assistance alarm should give a visual and "
  "audible signal, with a pull cord reachable from the wheelchair, the WC and the floor. General lighting level "
  "should be 200-300 lux at floor level. Floor surfaces should be firm, level and slip resistant. A shelf and two "
  "clothes hooks (1050 mm and 1400 mm above floor) should be provided. A colostomy changing surface should be "
  "provided in all accessible WCs."),

c("1.4.5", "Wheelchair accessible unisex WC", 86,
  "Minimum room dimensions 1800 mm x 2500 mm (1800 mm x 1800 mm turning space) or 1500 mm x 2200 mm (1500 mm x "
  "1500 mm turning space) for small buildings. A distance of 750 mm should be provided from the back wall to the "
  "front of the WC pan so the wheelchair can reverse in parallel. The finger-rinse basin should be 140-160 mm "
  "from the front of the WC pan. Grab rails at least 600 mm long, contrasting visually with the background."),

c("1.4.6.1", "Standard WC cubicles", 92,
  "Where standard cubicles have inward-opening doors, a minimum 450 mm diameter manoeuvring space should be "
  "provided between the door swing, the WC pan and the side wall."),

c("1.4.6.2", "Cubicles for ambulant disabled people", 92,
  "Cubicle width between 800 mm and 900 mm, WC centrally located on the back wall, an activity space of 750 mm "
  "clear of the door swing, horizontal and vertical grab rails on both sides of the WC pan, and a colostomy "
  "changing surface."),

c("1.4.6.3", "Enlarged Cubicles", 93,
  "Minimum cubicle width 1200 mm, WC centreline 450-500 mm from one wall, 750 mm activity space clear of the "
  "door swing, horizontal and vertical grab rails adjacent to the WC pan and on the rear wall, and a colostomy "
  "changing surface."),

c("1.4.7", "Accessible Urinals", 96,
  "A clear level area of 900 mm x 1400 mm in front of a wheelchair-accessible urinal, rim 380 mm above floor "
  "level (500 mm for ambulant disabled people). Vertical grab rails on both sides: 600 mm long for standing "
  "users, 900 mm long for wheelchair users, top fixings at 1400 mm above floor level."),

c("1.4.8", "Accessible Bathrooms/Shower Rooms", 98,
  "A shower area should have wall-mounted drop-down support rails and a slip-resistant tip-up seat. A bath "
  "should have a transfer seat 400 mm deep, equal to the bath width. The washbasin should be approximately 500 "
  "mm wide x 450 mm deep, rim 720-740 mm above floor, with a waste plug and clear knee space beneath."),

c("1.4.9.1", "Changing Facilities", 102,
  "Overall dimensions and equipment/control layout for an individual self-contained changing unit should follow "
  "the dimensioned diagram; the floor should be level and a 1500 mm deep manoeuvring space provided in front of "
  "any communal lockers."),

c("1.4.9.2", "Showering Facilities", 102,
  "The shower curtain/enclosure should be operable from the shower seat and enclose the seat and grab rails when "
  "in a horizontal position. The floor should be self-draining. Shower controls should be easy to use and "
  "operable with a closed fist."),

c("1.4.10", "Changing Places Toilets", 105,
  "A peninsular WC layout with clear circulation space on both sides is required, 750 mm from the back wall to "
  "the front of the WC pan, drop-down support rails and vertical grab rails (minimum 600 mm) on both sides. An "
  "1800 mm x 2000 mm wheelchair turning space, free from obstruction, should be provided directly inside the "
  "door. A power-operated, height-adjustable wash-hand basin (approx. 500 mm x 450 mm, adjustable 600-850 mm) "
  "with vertical grab rails is required. A wall-mounted, height-adjustable adult-sized changing bench, at least "
  "1800 mm x 800 mm, adjustable 450-900 mm, rated for a safe working load of not less than 200 kg, with "
  "retractable side safety rails, is required, along with a full-room-cover overhead tracked hoist system (I.S. "
  "EN ISO 10535) rated for at least 200 kg with at least 2100 mm headroom under the track. An emergency "
  "assistance alarm system with two pull cords is required, plus a retractable privacy screen at least 1750 mm "
  "long, and signage on safe operation of the equipment. Where sanitary facilities combining showers and WCs are "
  "otherwise provided, a shower unit should also be included in the changing places toilet."),

c("1.5.2", "Other Facilities — Introduction", 114,
  "Provisions should ensure that facilities within a building (audience/spectator seating, refreshment "
  "facilities, sleeping accommodation, switches/outlets/controls) are accessible to visitors and staff with a "
  "wide range of abilities, including people with vision, hearing, intellectual or mobility impairments and "
  "people with buggies."),

c("1.5.3", "Audience and spectator facilities with fixed seating", 116,
  "At least one set of wheelchair spaces should be provided in pairs with standard seating on at least one "
  "side, to avoid segregation; minimum provision follows Table 4 (roughly 1% of total seating capacity, with a "
  "minimum of 6 spaces for smaller venues via removable seating). Clear space allowance for an occupied "
  "wheelchair is 900 mm x 1400 mm deep; the floor of each wheelchair space should be level, with a hearing "
  "enhancement system provided."),

c("1.5.4", "Audience and Spectator Facilities without Fixed Seating", 118,
  "Where a raised podium or stage is provided, wheelchair users should have access to it by ramp or lifting "
  "platform, and a hearing enhancement system should be provided (except in primary/post-primary classrooms or "
  "standard office meeting rooms)."),

c("1.5.5", "Refreshment Facilities", 120,
  "A section of a bar or serving counter at least 1500 mm long should be permanently accessible to wheelchair "
  "users at a level of not more than 850 mm above the floor, with a minimum clear manoeuvring space of 1800 mm x "
  "1800 mm in front, outside any circulation route."),

c("1.5.6", "Accessible Sleeping Accommodation", 121,
  "One guest bedroom in every twenty (minimum one) should be suitable in size, layout and facilities for "
  "independent use by people with a wide range of abilities, with the same proportion having ensuite sanitary "
  "facilities. Entrance door minimum effective clear width 800 mm; a visual fire alarm signal and visual "
  "door-knock indicator should be provided; an emergency assistance alarm activated by a pull cord should be "
  "operable from the bed and an adjacent floor area."),

c("1.5.7", "Switches, Outlets and Controls", 123,
  "Socket outlets should be located between 400 mm and 1200 mm above the floor (lower end preferred); light "
  "switches and permanently wired appliance switches between 400 mm and 1200 mm; controls needing precise hand "
  "movement between 750 mm and 1200 mm; simple push-button controls not more than 1200 mm; emergency alarm pull "
  "cords coloured red with bangles at 100 mm and 800-1000 mm above the floor; controls needing close vision "
  "(meters, thermostats) between 1200 mm and 1400 mm. Controls should contrast visually with their background."),

c("1.6.3", "Signage", 127,
  "Signs should be clear, short and concise; text should not be set entirely in capital letters. The "
  "International Symbol for Access should be used on signs to accessible entrances, routes, sanitary and other "
  "facilities. Tactile signage (embossed text, symbols, Braille) is required for key location information at a "
  "touchable height."),

c("1.6.4", "Visual contrast", 128,
  "The difference in Light Reflectance Value (LRV) between adjoining surfaces should be 30 points or more "
  "(20 points or more for large areas such as walls and floors, provided illuminance is at least 200 lux); "
  "15 points or more for door opening furniture against its background."),

c("1.6.5", "Lighting", 129,
  "Artificial lighting should give good colour rendering of all surfaces and avoid glare, pools of bright light "
  "and strong shadows."),

c("1.6.6", "Audible aids", 129,
  "Hearing enhancement systems (induction loop, infra-red, radio) should preserve the source characteristics "
  "while suppressing reverberation and extraneous noise; the type installed should be indicated with clear "
  "signage, and public address systems should be supplemented by visual information."),

# ---------------------------------------------------------------------
# Section 2 — Access and Use of Existing Buildings Other than Dwellings
# ---------------------------------------------------------------------
c("2.0", "Introduction", 131,
  "Section 2 provides additional guidance on the minimum provisions for certain elements and features of "
  "existing buildings where it is not practicable to achieve the Section 1 provisions. Where works are carried "
  "out in accordance with Section 1, and Section 2 where necessary, this prima facie indicates compliance with "
  "Requirement M1."),

c("2.1.3", "Access Routes (existing buildings)", 133,
  "Section 1 guidance should be followed except where relaxed minimums apply in existing buildings: e.g. "
  "minimum clear width of a level or gently sloped route may reduce to 1000 mm where 1500 mm is not practicable; "
  "ramp top/bottom landings may reduce to 1500 mm x 1500 mm; stepped route goings may reduce to 280 mm; handrail "
  "heights may be 840-1000/1100 mm above the pitch line/landing where the original 900 mm minimum is not "
  "practicable."),

c("2.1.5", "On-site Car Parking (existing buildings)", 137,
  "Where it is not practicable to provide the full number of designated car parking spaces required by Section "
  "1.1.5, as many as possible should be provided but at least one, or alternatively a setting-down area should "
  "be provided."),

c("2.2.2", "Access to Existing Buildings — Introduction", 138,
  "Where it is not practicable for each applicable entrance to be accessible, alternative accessible entrance(s) "
  "should be provided or the internal planning revised; at least one entrance should be made accessible."),

c("2.2.4", "Accessible Entrance Doors (existing buildings)", 138,
  "Where it is not practicable to provide the Section 1 effective clear door width, it should be as wide as "
  "possible but not less than 750 mm — unless the frontage and entrance doors are being replaced, in which case "
  "full Section 1 compliance is required."),

c("2.3.3.2", "Internal Doors (existing buildings)", 140,
  "Where it is not practicable to provide the Section 1 effective clear door width, it should be as wide as "
  "possible but not less than 750 mm."),

c("2.3.3.3", "Corridors and Passageways (existing buildings)", 140,
  "Where it is not practicable to maintain the Section 1 minimum unobstructed corridor width, it should be as "
  "wide as possible but not less than 1000 mm."),

c("2.3.4.1", "Vertical Features — Provision (existing buildings)", 141,
  "Where it is not practicable to provide a passenger lift in an existing building, an enclosed vertical lifting "
  "platform (BS 6440:1999) should be provided instead; alternatively the same services/facilities available on "
  "other levels should be made available at the entry/accessible level."),

c("2.3.4.3", "Internal Stairs Suitable for Ambulant Disabled People (existing buildings)", 142,
  "Where a lifting device serves all floors, a stairs suitable for ambulant disabled people is not necessary. "
  "Where provided, the minimum clear width, landing length and step going may be relaxed relative to Section 1 "
  "(e.g. going not less than 250 mm) where full compliance is not practicable."),

c("2.4.3", "Sanitary Facilities — General Provisions (existing buildings)", 144,
  "Where there is more than one WC facility at different locations, at least one accessible unisex WC should be "
  "provided on each accessible floor with a WC facility. Where a full 1800 mm x 1800 mm turning space is not "
  "practicable, a 1500 mm x 1500 mm turning space may be provided. Where a changing places toilet cannot use the "
  "standard room layout, an alternative layout may be used provided the minimum wheelchair turning space and "
  "component circulation spaces are still provided."),

c("2.5.5", "Refreshment Facilities (existing buildings)", 146,
  "Where the Section 1 clear manoeuvring space is not practicable, a minimum of 1500 mm x 1500 mm should be "
  "provided in front of a counter or bar; where a fully accessible 1500 mm working surface cannot be provided, "
  "the counter should be as wide as possible but at least 900 mm long."),

c("2.6.2", "Aids to Communication (existing buildings)", 148,
  "Section 1 signage, visual contrast and audible aid guidance should be followed where practicable in existing "
  "buildings."),

# ---------------------------------------------------------------------
# Section 3 — Access and Use of Dwellings
# ---------------------------------------------------------------------
c("3.1.1", "Approach to Dwellings — Objective", 150,
  "The objective is to provide an adequate means of approach to the main entrance of a dwelling to facilitate "
  "visitors from a point of access."),

c("3.1.2", "Access Route to a Dwelling", 150,
  "The point of access is the entrance at the boundary of the dwelling plot, or the point at which a visitor "
  "would normally alight from a vehicle, where the distance from the boundary point of access to the main "
  "entrance is greater than 30 m, or the site gradient does not allow a suitable level/gently sloped/ramped "
  "approach. At least one approach route from a point of access to the main entrance should be an access route "
  "complying with 3.1.2.1-3.1.2.5."),

c("3.1.2.1", "Access Route to a Dwelling — General", 150,
  "The clear opening width of at least one point of access should be a minimum of 900 mm, and the access route "
  "leading from it should maintain a clear width of at least 900 mm with a firm, even, slip-reducing surface. "
  "Where the approach forms part of an on-site driveway, the driveway should be at least 3600 mm wide. A raised "
  "kerb at least 100 mm high should be provided on any open side where the ground is not graded to the "
  "approach. Minimum headroom on the approach route is 2100 mm."),

c("3.1.2.2", "Level Access Route (dwellings)", 151,
  "A level approach route (gradient 1:50 or less steep) accommodates the widest range of abilities and should "
  "be used where the dwelling design, within overall space constraints, minimises the difference in level "
  "between the dwelling entrance and the plot's point of access."),

c("3.1.2.3", "Gently Sloped Access Route (dwellings)", 151,
  "Where site gradients do not allow a level route, the flattest gradient achievable should be used; access "
  "routes of 1:20 or less steep are preferred. A gradient steeper than 1:50 but less steep than 1:20 is "
  "considered gently sloped."),

c("3.1.2.4", "Ramped Access Route (dwellings)", 151,
  "Where a ramp is necessary it should have the shallowest gradient practicable — 1:20 or steeper but not "
  "exceeding 1:12. Level landings should be provided between flights or at any change of direction, each at "
  "least 1200 mm long exclusive of any door/gate swing. Between 1:20 and 1:15 the maximum length between level "
  "landings is 10 m; between 1:15 and 1:12 it is 5 m."),

c("3.1.2.5", "Stepped Access Route (dwellings)", 152,
  "A stepped approach may be used where it is not practicable to provide the required level/gently "
  "sloped/ramped approach, e.g. where the gradient is steeper than 1:15, where space is insufficient for ramps "
  "and landings given the existing building line, where planning requirements exist (e.g. flood plains), or "
  "where the dwelling entrance is above ground floor level (e.g. duplex buildings — note the ground floor level "
  "of a duplex should not use a stepped approach). Where used it should be suitable for ambulant disabled "
  "people: minimum unobstructed width 900 mm between handrails; rise of a flight between landings not more than "
  "1800 mm; top/bottom (and intermediate) landings at least 900 mm long, clear of door swings; step rise uniform "
  "between 100 mm and 150 mm; step going uniform and not less than 280 mm; tapered steps avoided (or, if "
  "necessary, situated at the bottom with a going of at least 280 mm measured 270 mm from the narrow edge); a "
  "continuous handrail on both sides where the flight has three or more risers (not required for a shallow "
  "stepped approach with goings at least 750 mm long)."),

c("3.2.1", "Access to Dwellings — Objective", 154,
  "The objective is to provide a main entrance to a dwelling that is accessible to visitors."),

c("3.2.2", "Accessible Entrance (dwellings)", 154,
  "The main entrance is the entrance a visitor unfamiliar with the dwelling would normally expect to approach. "
  "Where it is not practicable for the main entrance to be accessible, an alternative entrance within the public "
  "realm of the dwelling plot, approached via a compliant access route and suitable for wheelchair users, should "
  "be accessible instead. A clear level area at least 1200 mm x 1200 mm should be provided in front of every "
  "accessible entrance. The entrance should have a level entry (maximum threshold height 15 mm, chamfered or "
  "pencil-rounded exposed edges). The minimum effective clear opening width of the entrance door should be 800 "
  "mm. In exceptional circumstances where a level entry is not practicable (e.g. insufficient space to conform "
  "to the existing building line, or no habitable room at entrance-storey level), one or more steps may be used "
  "instead."),

c("3.3.1", "Circulation within Dwellings — Objective", 156,
  "The objective is to facilitate circulation of visitors within the entrance storey, or, where there is no "
  "habitable room at that level, within the storey containing the main living room."),

c("3.3.2.1", "Horizontal Circulation within a Dwelling", 156,
  "Corridors and passageways should have a minimum unobstructed width of not less than 900 mm (localised "
  "obstructions such as radiators are allowed provided the width there is at least 800 mm and the obstruction "
  "is not opposite a door). Doors to accessible habitable rooms: minimum effective clear width 775 mm requires a "
  "minimum unobstructed corridor width of 1050 mm (900 mm if approached head-on); 800 mm effective clear width "
  "requires 900 mm corridor width. At least 1200 mm of unobstructed corridor should approach any door. Doors to "
  "rooms accessed only via steps or stairs (other than cloak rooms, hot presses etc.) may have a minimum "
  "effective clear width of 750 mm. Saddle boards should be bevelled with a maximum upstand of 10 mm. Door "
  "handles between 800 mm and 1200 mm above floor level (900 mm preferred). Where a stepped change of level "
  "exists within the storey, it should be positioned so at least one habitable room and a room containing a WC "
  "can be reached from the accessible entrance without negotiating the step(s)."),

c("3.3.2.2", "Vertical Circulation within a Dwelling", 159,
  "Where there is no habitable room at entry level, the stairway to the storey containing the main living room "
  "should have: minimum unobstructed width not less than 900 mm between handrails; rise of a flight between "
  "landings not more than 1800 mm; top, bottom and (if necessary) intermediate landings at least 900 mm long; "
  "step rise uniform and not more than 175 mm; step going uniform and not less than 280 mm; tapered steps "
  "avoided (or situated at the bottom with a going not less than 280 mm measured 270 mm from the narrow edge); a "
  "continuous handrail on both sides where the flight has three or more risers."),

c("3.4.1", "Sanitary Facilities for Dwellings — Objective", 160,
  "The objective is to provide a WC that is accessible to visitors."),

c("3.4.2", "Accessible WC (dwellings)", 160,
  "A WC should be provided at entry level or, where there is no habitable room at that level, in the storey "
  "containing the main living room, located so it can be reached from the accessible entrance and from at least "
  "one habitable room without negotiating steps. A clear space of 750 mm by 1200 mm, accessible by a wheelchair "
  "user, should be available adjacent to the WC to facilitate sideways transfer. The size and layout of the "
  "bathroom or WC compartment, and the door position, should allow a wheelchair to be fully contained within the "
  "compartment with the door closed with the wheelchair inside. General headroom in the WC compartment should be "
  "2100 mm minimum."),

c("3.4.3", "WC in Smaller Dwellings", 162,
  "In certain smaller dwellings (where the storey area containing the WC is less than 45 m2), a reduced WC "
  "compartment layout is acceptable per Diagram 37, with minimum headroom 2100 mm measured from the front of the "
  "pan, and door width per Table 5; a door wider than the minimum, or an outward-opening, folding or sliding "
  "door, generally assists wheelchair access."),

c("3.5.1", "Switches and Sockets in Dwellings — Objective", 163,
  "The objective is that switches and socket outlets should be located at accessible heights and are easy to "
  "operate in the accessible areas of a dwelling."),

c("3.5.2", "Switches and Sockets (dwellings)", 163,
  "Electric light switches in accessible areas should be located between 900 mm and 1200 mm above floor level. "
  "Equipment assisting entry (doorbells, entry phones, intercoms) should be located between 900 mm and 1200 mm "
  "above floor level. Switches and socket outlets for lighting and other equipment in accessible areas should be "
  "located between 400 mm and 1200 mm above finished floor level, restricted to general-purpose convenience "
  "outlets rather than dedicated continuously-connected appliance outlets."),
]

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(CLAUSES, fh, indent=1)
    print(f"wrote {len(CLAUSES)} clauses to {OUT}")
