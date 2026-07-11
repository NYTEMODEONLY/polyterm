// ============================================================
// Balkan Civilizations — static game data
// ============================================================
"use strict";

const TERRAIN = {
  OCEAN:     { name: "Sea",       food: 1, prod: 0, gold: 1, moveCost: 99, passable: false, color: "#1b4965", defense: 0 },
  COAST:     { name: "Coast",     food: 2, prod: 0, gold: 1, moveCost: 99, passable: false, color: "#2d6a8f", defense: 0 },
  GRASSLAND: { name: "Grassland", food: 2, prod: 0, gold: 0, moveCost: 1,  passable: true,  color: "#5a8f3c", defense: 0 },
  PLAINS:    { name: "Plains",    food: 1, prod: 1, gold: 0, moveCost: 1,  passable: true,  color: "#a09045", defense: 0 },
  HILLS:     { name: "Hills",     food: 0, prod: 2, gold: 0, moveCost: 2,  passable: true,  color: "#8a7a52", defense: 0.25 },
  MOUNTAIN:  { name: "Mountains", food: 0, prod: 0, gold: 0, moveCost: 99, passable: false, color: "#6e6e72", defense: 0 },
};

// Features sit on top of terrain
const FEATURE = {
  FOREST: { name: "Forest", food: 0, prod: 1, gold: 0, moveCost: 2, defense: 0.25, color: "#2e5b2e" },
};

const RESOURCE = {
  WHEAT:  { name: "Wheat",  icon: "🌾", food: 2, prod: 0, gold: 0, terrains: ["GRASSLAND", "PLAINS"] },
  SHEEP:  { name: "Sheep",  icon: "🐑", food: 1, prod: 1, gold: 0, terrains: ["HILLS", "GRASSLAND"] },
  HORSES: { name: "Horses", icon: "🐎", food: 0, prod: 1, gold: 1, terrains: ["GRASSLAND", "PLAINS"] },
  IRON:   { name: "Iron",   icon: "⚒️", food: 0, prod: 2, gold: 0, terrains: ["HILLS", "PLAINS"] },
  WINE:   { name: "Wine",   icon: "🍇", food: 1, prod: 0, gold: 2, terrains: ["GRASSLAND", "PLAINS", "HILLS"], luxury: true },
  SILVER: { name: "Silver", icon: "🪙", food: 0, prod: 1, gold: 2, terrains: ["HILLS"], luxury: true },
  OLIVES: { name: "Olives", icon: "🫒", food: 1, prod: 0, gold: 2, terrains: ["GRASSLAND", "PLAINS"], luxury: true },
  SALT:   { name: "Salt",   icon: "🧂", food: 0, prod: 1, gold: 2, terrains: ["PLAINS", "HILLS"], luxury: true },
  FISH:   { name: "Fish",   icon: "🐟", food: 2, prod: 0, gold: 1, terrains: ["COAST"] },
};

// Empire happiness tuning
const HAPPINESS = {
  base: 12,            // baseline contentment
  perLuxury: 4,        // each distinct luxury type you control
  perCity: 2,          // unhappiness per city
  perPop: 0.4,         // unhappiness per citizen
  strikeAt: -10,       // below this: -15% combat strength, growth stops
};
const GOLDEN_AGE = {
  threshold: (n) => 400 + 250 * n,  // meter cost of the (n+1)th golden age
  duration: 10,
  bonus: 0.2,          // +20% gold and production
};

// ------------------------------------------------------------
// Technology tree
// ------------------------------------------------------------
const ERAS = ["Ancient", "Classical", "Medieval", "Renaissance"];

const TECHS = {
  AGRICULTURE:      { name: "Agriculture",      era: 0, cost: 20,  req: [] },
  POTTERY:          { name: "Pottery",          era: 0, cost: 35,  req: ["AGRICULTURE"] },
  SAILING:          { name: "Sailing",          era: 0, cost: 35,  req: ["AGRICULTURE"] },
  ANIMAL_HUSBANDRY: { name: "Animal Husbandry", era: 0, cost: 35,  req: ["AGRICULTURE"] },
  ARCHERY:          { name: "Archery",          era: 0, cost: 35,  req: ["AGRICULTURE"] },
  MINING:           { name: "Mining",           era: 0, cost: 35,  req: ["AGRICULTURE"] },
  WRITING:          { name: "Writing",          era: 0, cost: 55,  req: ["POTTERY"] },
  THE_WHEEL:        { name: "The Wheel",        era: 0, cost: 55,  req: ["ANIMAL_HUSBANDRY"] },
  BRONZE_WORKING:   { name: "Bronze Working",   era: 0, cost: 55,  req: ["MINING"] },
  MASONRY:          { name: "Masonry",          era: 0, cost: 55,  req: ["MINING"] },
  PHILOSOPHY:       { name: "Philosophy",       era: 1, cost: 110,  req: ["WRITING"] },
  HORSEBACK_RIDING: { name: "Horseback Riding", era: 1, cost: 110,  req: ["THE_WHEEL"] },
  CURRENCY:         { name: "Currency",         era: 1, cost: 110,  req: ["THE_WHEEL", "BRONZE_WORKING"] },
  IRON_WORKING:     { name: "Iron Working",     era: 1, cost: 110,  req: ["BRONZE_WORKING"] },
  MATHEMATICS:      { name: "Mathematics",      era: 1, cost: 150, req: ["WRITING", "THE_WHEEL"] },
  COMPASS:          { name: "Compass",          era: 1, cost: 150, req: ["SAILING", "MATHEMATICS"] },
  CONSTRUCTION:     { name: "Construction",     era: 1, cost: 150, req: ["MASONRY", "MATHEMATICS"] },
  THEOLOGY:         { name: "Theology",         era: 2, cost: 260, req: ["PHILOSOPHY"] },
  CIVIL_SERVICE:    { name: "Civil Service",    era: 2, cost: 260, req: ["PHILOSOPHY", "CURRENCY"] },
  CHIVALRY:         { name: "Chivalry",         era: 2, cost: 330, req: ["HORSEBACK_RIDING", "CIVIL_SERVICE"] },
  MACHINERY:        { name: "Machinery",        era: 2, cost: 330, req: ["CONSTRUCTION", "IRON_WORKING"] },
  STEEL:            { name: "Steel",            era: 2, cost: 330, req: ["IRON_WORKING", "CONSTRUCTION"] },
  EDUCATION:        { name: "Education",        era: 2, cost: 400, req: ["THEOLOGY", "CIVIL_SERVICE"] },
  PHYSICS:          { name: "Physics",          era: 2, cost: 400, req: ["MACHINERY", "STEEL"] },
  BANKING:          { name: "Banking",          era: 3, cost: 540, req: ["EDUCATION", "CHIVALRY"] },
  GUNPOWDER:        { name: "Gunpowder",        era: 3, cost: 650, req: ["PHYSICS", "EDUCATION"] },
};

// ------------------------------------------------------------
// Units.  cs = melee combat strength, rs = ranged strength
// ------------------------------------------------------------
const UNITS = {
  SETTLER:    { name: "Settler",       icon: "⛺", cost: 90,  cs: 0,  moves: 2, civilian: true },
  WORKER:     { name: "Worker",        icon: "🔨", cost: 60,  cs: 0,  moves: 2, civilian: true, worker: true },
  SCOUT:      { name: "Scout",         icon: "👁️", cost: 30,  cs: 5,  moves: 3, sight: 3 },
  WARRIOR:    { name: "Warrior",       icon: "🪓", cost: 40,  cs: 8,  moves: 2, upgrade: "SWORDSMAN", },
  ARCHER:     { name: "Archer",        icon: "🏹", cost: 45,  cs: 5,  rs: 8,  range: 2, moves: 2, tech: "ARCHERY", upgrade: "COMPOSITE", },
  SPEARMAN:   { name: "Spearman",      icon: "🔱", cost: 55,  cs: 11, moves: 2, tech: "BRONZE_WORKING", upgrade: "PIKEMAN", },
  HORSEMAN:   { name: "Horseman",      icon: "🐎", cost: 70,  cs: 12, moves: 4, tech: "HORSEBACK_RIDING", needs: "HORSES", upgrade: "KNIGHT", },
  SWORDSMAN:  { name: "Swordsman",     icon: "🗡️", cost: 75,  cs: 14, moves: 2, tech: "IRON_WORKING", needs: "IRON", upgrade: "LONGSWORD", },
  CATAPULT:   { name: "Catapult",      icon: "🪨", cost: 75,  cs: 4,  rs: 14, range: 2, moves: 2, tech: "MATHEMATICS", siege: true, upgrade: "TREBUCHET", },
  COMPOSITE:  { name: "Composite Bowman", icon: "🏹", cost: 80, cs: 7, rs: 11, range: 2, moves: 2, tech: "CONSTRUCTION", upgrade: "CROSSBOW", },
  PIKEMAN:    { name: "Pikeman",       icon: "🛡️", cost: 90,  cs: 16, moves: 2, tech: "CIVIL_SERVICE" },
  KNIGHT:     { name: "Knight",        icon: "🐴", cost: 120, cs: 20, moves: 4, tech: "CHIVALRY", needs: "HORSES" },
  CROSSBOW:   { name: "Crossbowman",   icon: "🎯", cost: 120, cs: 13, rs: 18, range: 2, moves: 2, tech: "MACHINERY" },
  LONGSWORD:  { name: "Longswordsman", icon: "⚔️", cost: 130, cs: 21, moves: 2, tech: "STEEL", needs: "IRON", upgrade: "MUSKETMAN", },
  TREBUCHET:  { name: "Trebuchet",     icon: "🏰", cost: 130, cs: 6,  rs: 20, range: 2, moves: 2, tech: "PHYSICS", siege: true },
  MUSKETMAN:  { name: "Musketman",     icon: "🔫", cost: 160, cs: 24, moves: 2, tech: "GUNPOWDER" },
  // ---- Naval units (built in coastal cities only) ----
  GALLEY:     { name: "Galley",        icon: "⛵", cost: 60,  cs: 10, moves: 4, tech: "SAILING", naval: true, coastOnly: true, upgrade: "GALLEASS", },
  GALLEASS:   { name: "War Galleass",  icon: "🚢", cost: 110, cs: 12, rs: 17, range: 2, moves: 5, tech: "COMPASS", naval: true },
  // ---- Trade ----
  CARAVAN:    { name: "Caravan",       icon: "🐫", cost: 70, cs: 0, moves: 2, civilian: true, caravan: true, tech: "CURRENCY" },
  // ---- Religious units (purchased with faith, not production) ----
  MISSIONARY: { name: "Missionary",    icon: "🙏", cost: 0, faithCost: 120, cs: 0, moves: 4, civilian: true, missionary: true, charges: 2 },
  // ---- Great People (earned, never built) ----
  GREAT_SCIENTIST: { name: "Great Scientist", icon: "🔭", cost: 0, cs: 0, moves: 3, civilian: true, great: "sci" },
  GREAT_ENGINEER:  { name: "Great Engineer",  icon: "🏗️", cost: 0, cs: 0, moves: 3, civilian: true, great: "eng" },
  GREAT_GENERAL:   { name: "Great General",   icon: "🎖️", cost: 0, cs: 0, moves: 4, civilian: true, great: "gen" },
  // ---- Unique units ----
  GUSAR:      { name: "Gusar",         icon: "🐎", cost: 110, cs: 19, moves: 5, tech: "CHIVALRY", uu: "SERBIA", replaces: "KNIGHT",
                blurb: "Serbian light cavalry. Faster than the Knight and needs no horses." },
  KONNIK:     { name: "Konnik",        icon: "🐎", cost: 70,  cs: 14, moves: 4, tech: "HORSEBACK_RIDING", uu: "BULGARIA", replaces: "HORSEMAN", needs: "HORSES",
                blurb: "Bulgar heavy horseman. Stronger than the Horseman." },
  CATAPHRACT: { name: "Cataphract",    icon: "🐴", cost: 120, cs: 23, moves: 3, tech: "CHIVALRY", uu: "BYZANTIUM", replaces: "KNIGHT", needs: "HORSES",
                blurb: "Byzantine armoured cavalry. Much stronger than the Knight." },
  JANISSARY:  { name: "Janissary",     icon: "🔫", cost: 160, cs: 26, moves: 2, tech: "GUNPOWDER", uu: "OTTOMAN", replaces: "MUSKETMAN", healOnKill: 50,
                blurb: "Elite Ottoman infantry. Stronger than the Musketman and heals 50 HP on a kill." },
  STRADIOT:   { name: "Stradiot",      icon: "🐎", cost: 70,  cs: 12, moves: 4, tech: "HORSEBACK_RIDING", uu: "ALBANIA", replaces: "HORSEMAN", terrainBonus: 0.25,
                blurb: "Albanian light horseman. Fights +25% in hills and forest, needs no horses." },
  USKOK:      { name: "Uskok",         icon: "🗡️", cost: 75,  cs: 14, moves: 3, tech: "IRON_WORKING", uu: "CROATIA", replaces: "SWORDSMAN",
                blurb: "Croatian raider. A faster Swordsman that needs no iron." },
  CALARASI:   { name: "Călărași",      icon: "🐎", cost: 115, cs: 20, moves: 4, tech: "CHIVALRY", uu: "WALLACHIA", replaces: "KNIGHT", healOnKill: 30,
                blurb: "Wallachian border cavalry. Heals 30 HP on a kill." },
  KRSTJANI:   { name: "Krstjani Guard", icon: "🛡️", cost: 85, cs: 18, moves: 2, tech: "CIVIL_SERVICE", uu: "BOSNIA", replaces: "PIKEMAN",
                blurb: "Bosnian church militia. Stronger than the Pikeman." },
  SAMUIL_GUARD: { name: "Samuil's Guard", icon: "🔱", cost: 55, cs: 13, moves: 2, tech: "BRONZE_WORKING", uu: "MACEDONIA", replaces: "SPEARMAN", defendBonus: 0.25,
                blurb: "Tsar Samuil's fortress infantry. Stronger than the Spearman and +25% when defending." },
};

// ------------------------------------------------------------
// Tile improvements (built by Workers)
// ------------------------------------------------------------
const IMPROVEMENT = {
  FARM: { name: "Farm", icon: "🌱", turns: 4, tech: "AGRICULTURE", terrains: ["GRASSLAND", "PLAINS"], food: 1 },
  MINE: { name: "Mine", icon: "⛏️", turns: 4, tech: "MINING",      terrains: ["HILLS"],               prod: 1 },
  ROAD: { name: "Road", icon: "🛤️", turns: 3, tech: "THE_WHEEL",   terrains: ["GRASSLAND", "PLAINS", "HILLS"], road: true },
};

// ------------------------------------------------------------
// Buildings & wonders
// ------------------------------------------------------------
const BUILDINGS = {
  MONUMENT:  { name: "Monument",   icon: "🗿", cost: 45,  culture: 2 },
  SHRINE:    { name: "Shrine",     icon: "🕯️", cost: 45,  faith: 2, tech: "POTTERY" },
  GRANARY:   { name: "Granary",    icon: "🌾", cost: 65,  food: 2, tech: "POTTERY" },
  BARRACKS:  { name: "Barracks",   icon: "⚔️", cost: 70,  prod: 2, tech: "BRONZE_WORKING" },
  LIBRARY:   { name: "Library",    icon: "📜", cost: 80,  sci: 3, tech: "WRITING" },
  WALLS:     { name: "Walls",      icon: "🧱", cost: 80,  cityHp: 50, cityStr: 4, tech: "MASONRY" },
  MARKET:    { name: "Market",     icon: "💰", cost: 100, gold: 3, tech: "CURRENCY" },
  TAVERN:    { name: "Tavern",     icon: "🍺", cost: 100, happy: 3, tech: "CURRENCY" },
  HAMMAM:    { name: "Hammam",     icon: "🛁", cost: 140, happy: 3, tech: "THEOLOGY" },
  TEMPLE:    { name: "Temple",     icon: "⛪", cost: 90,  culture: 3, faith: 2, tech: "PHILOSOPHY" },
  AQUEDUCT:  { name: "Aqueduct",   icon: "⛲", cost: 110, food: 3, tech: "CONSTRUCTION" },
  FORGE:     { name: "Forge",      icon: "🔥", cost: 120, prod: 3, tech: "IRON_WORKING" },
  UNIVERSITY:{ name: "University", icon: "🎓", cost: 160, sci: 6, tech: "EDUCATION" },
  CASTLE:    { name: "Castle",     icon: "🏯", cost: 160, cityHp: 75, cityStr: 6, tech: "CHIVALRY", requires: "WALLS" },
  WORKSHOP:  { name: "Workshop",   icon: "🛠️", cost: 150, prod: 4, tech: "MACHINERY" },
  BANK:      { name: "Bank",       icon: "🏦", cost: 200, gold: 5, tech: "BANKING" },
  // ---- Wonders (one per world) ----
  DIOCLETIAN:   { name: "Diocletian's Palace",  icon: "🏛️", cost: 170, wonder: true, gold: 3, culture: 3, tech: "MASONRY",
                  blurb: "The emperor's retirement estate at Split. +3 gold, +3 culture." },
  HIPPODROME:   { name: "Hippodrome",           icon: "🏇", cost: 190, wonder: true, happy: 4, culture: 2, tech: "HORSEBACK_RIDING",
                  blurb: "Constantinople's arena of factions. +4 happiness, +2 culture." },
  OHRID_SCHOOL: { name: "Ohrid Literary School", icon: "📖", cost: 200, wonder: true, sci: 4, culture: 2, tech: "PHILOSOPHY",
                  blurb: "Cradle of Slavic letters. +4 science, +2 culture." },
  STARI_MOST:   { name: "Stari Most",           icon: "🌉", cost: 210, wonder: true, gold: 4, happy: 2, tech: "CONSTRUCTION",
                  blurb: "The old bridge at Mostar. +4 gold, +2 happiness." },
  MOUNT_ATHOS:  { name: "Mount Athos",          icon: "⛰️", cost: 240, wonder: true, faith: 5, culture: 3, tech: "THEOLOGY",
                  blurb: "The Holy Mountain of monasteries. +5 faith, +3 culture." },
  BRAN_CASTLE:  { name: "Bran Castle",          icon: "🦇", cost: 230, wonder: true, cityHp: 75, cityStr: 6, culture: 2, tech: "CHIVALRY",
                  blurb: "The Carpathian eyrie. +75 city HP, +6 city strength, +2 culture." },
  HAGIA_SOPHIA: { name: "Hagia Sophia",         icon: "🕌", cost: 260, wonder: true, culture: 6, sci: 3, faith: 4, tech: "THEOLOGY",
                  blurb: "The great church of Constantinople. +6 culture, +3 science." },
  STUDENICA:    { name: "Studenica Monastery",  icon: "⛪", cost: 210, wonder: true, culture: 5, food: 2, faith: 3, tech: "PHILOSOPHY",
                  blurb: "Jewel of Serbian Orthodoxy. +5 culture, +2 food." },
  RILA:         { name: "Rila Monastery",       icon: "🏔️", cost: 230, wonder: true, sci: 5, culture: 2, faith: 3, tech: "THEOLOGY",
                  blurb: "Bulgaria's mountain sanctuary. +5 science, +2 culture." },
  KALEMEGDAN:   { name: "Kalemegdan Fortress",  icon: "🏰", cost: 240, wonder: true, cityHp: 100, cityStr: 8, tech: "CHIVALRY",
                  blurb: "The white fortress over the Danube. +100 city HP, +8 city strength." },
};

// ------------------------------------------------------------
// Civilizations
// ------------------------------------------------------------
const CIVS = {
  SERBIA: {
    name: "Serbia", leader: "Stefan Dušan", adj: "Serbian",
    color: "#c0392b", color2: "#f5e6c8",
    trait: "Tsar of Serbs and Greeks", traitDesc: "+25% production toward buildings in every city.",
    buildingProdBonus: 0.25, uu: "GUSAR",
    cities: ["Beograd", "Prizren", "Niš", "Novo Brdo", "Kruševac", "Smederevo", "Peć", "Ras", "Priština", "Golubac"],
  },
  BULGARIA: {
    name: "Bulgaria", leader: "Simeon I the Great", adj: "Bulgarian",
    color: "#2e8b57", color2: "#ffffff",
    trait: "Golden Age of Simeon", traitDesc: "+2 science in every city.",
    cityScience: 2, uu: "KONNIK",
    cities: ["Preslav", "Tarnovo", "Sofia", "Plovdiv", "Pliska", "Varna", "Ohrid", "Vidin", "Silistra", "Burgas"],
  },
  BYZANTIUM: {
    name: "Byzantium", leader: "Basil II", adj: "Byzantine",
    color: "#6a0dad", color2: "#ffd700",
    trait: "The Purple Bureaucracy", traitDesc: "+4 gold in the capital, +1 gold in every other city.",
    capitalGold: 4, cityGold: 1, uu: "CATAPHRACT",
    cities: ["Constantinople", "Thessalonica", "Adrianople", "Nicaea", "Dyrrachium", "Corinth", "Athens", "Smyrna", "Trebizond", "Mystras"],
  },
  OTTOMAN: {
    name: "Ottomans", leader: "Mehmed II", adj: "Ottoman",
    color: "#b03a2e", color2: "#27ae60",
    trait: "Ghazi Warriors", traitDesc: "+20% combat strength when attacking cities.",
    vsCityBonus: 0.2, uu: "JANISSARY",
    cities: ["Edirne", "Bursa", "Üsküdar", "Gallipoli", "Iznik", "Manisa", "Ankara", "Konya", "Amasya", "Sivas"],
  },
  ALBANIA: {
    name: "Albania", leader: "Skanderbeg", adj: "Albanian",
    color: "#8b0000", color2: "#111111",
    trait: "Lord of the Mountains", traitDesc: "+30% combat strength when fighting in hills or forest.",
    roughBonus: 0.3, uu: "STRADIOT",
    cities: ["Krujë", "Shkodër", "Durrës", "Berat", "Vlorë", "Lezhë", "Gjirokastër", "Elbasan", "Korçë", "Tiranë"],
  },
  CROATIA: {
    name: "Croatia", leader: "Tomislav", adj: "Croatian",
    color: "#1f618d", color2: "#e74c3c",
    trait: "Adriatic Kingdom", traitDesc: "+2 gold and +1 food in cities founded next to the sea.",
    coastalGold: 2, coastalFood: 1, uu: "USKOK",
    cities: ["Zagreb", "Split", "Dubrovnik", "Zadar", "Nin", "Šibenik", "Knin", "Osijek", "Rijeka", "Trogir"],
  },
  WALLACHIA: {
    name: "Wallachia", leader: "Vlad III Drăculea", adj: "Wallachian",
    color: "#4a235a", color2: "#c0392b",
    trait: "Forest of the Impaled", traitDesc: "+25% combat strength inside your own territory.",
    homeBonus: 0.25, uu: "CALARASI",
    cities: ["Târgoviște", "București", "Curtea de Argeș", "Craiova", "Pitești", "Brăila", "Giurgiu", "Ploiești", "Câmpulung", "Snagov"],
  },
  MACEDONIA: {
    name: "Macedonia", leader: "Tsar Samuil", adj: "Macedonian",
    color: "#d35400", color2: "#f1c40f",
    trait: "Ohrid Archbishopric", traitDesc: "+2 culture and +1 science in every city.",
    cityCulture: 2, cityScience: 1, uu: "SAMUIL_GUARD",
    cities: ["Ohrid", "Skopje", "Bitola", "Prilep", "Struga", "Štip", "Strumica", "Tetovo", "Veles", "Kratovo"],
  },
  BOSNIA: {
    name: "Bosnia", leader: "Tvrtko I", adj: "Bosnian",
    color: "#b7950b", color2: "#154360",
    trait: "Crown of Three Lands", traitDesc: "+50% culture in every city (faster border growth).",
    cultureBonus: 0.5, uu: "KRSTJANI",
    cities: ["Visoko", "Jajce", "Sarajevo", "Srebrenica", "Travnik", "Bobovac", "Mostar", "Banja Luka", "Tuzla", "Zenica"],
  },
};

const CIV_IDS = Object.keys(CIVS);

// Colorblind-safe civ palette (Okabe-Ito derived, distinct under deutan/
// protan/tritan vision and legible on the dark map). Applied by swapping
// CIVS[id].color/color2 in place when the accessibility toggle is on.
const COLORBLIND_PALETTE = {
  SERBIA:    { color: "#E69F00", color2: "#4a3200" }, // orange
  BULGARIA:  { color: "#56B4E9", color2: "#0b3a52" }, // sky blue
  BYZANTIUM: { color: "#CC79A7", color2: "#4d2138" }, // reddish purple
  OTTOMAN:   { color: "#009E73", color2: "#00382a" }, // bluish green
  ALBANIA:   { color: "#D55E00", color2: "#4a2100" }, // vermillion
  CROATIA:   { color: "#0072B2", color2: "#00263b" }, // blue
  WALLACHIA: { color: "#F0E442", color2: "#4a4600" }, // yellow
  BOSNIA:    { color: "#999999", color2: "#2b2b2b" }, // grey
  MACEDONIA: { color: "#CA9161", color2: "#402d18" }, // tan
};

// ------------------------------------------------------------
// Religion
// ------------------------------------------------------------
const RELIGION_NAMES = [
  { name: "Orthodoxy",   icon: "☦️" },
  { name: "Catholicism", icon: "✝️" },
  { name: "Islam",       icon: "☪️" },
  { name: "Bogomilism",  icon: "🔥" },
  { name: "Tengrism",    icon: "🌞" },
  { name: "Hellenism",   icon: "⚡" },
];

// Which faith each civ founds by preference (AI; default offering for you)
const CIV_RELIGION = {
  SERBIA: "Orthodoxy", BULGARIA: "Orthodoxy", BYZANTIUM: "Orthodoxy",
  MACEDONIA: "Orthodoxy", WALLACHIA: "Orthodoxy",
  CROATIA: "Catholicism", ALBANIA: "Catholicism",
  OTTOMAN: "Islam", BOSNIA: "Bogomilism",
};

const BELIEFS = {
  HEARTH:  { name: "Sacred Hearths", desc: "+2 food in your cities that follow the religion" },
  SCHOLAR: { name: "Divine Wisdom",  desc: "+2 science in your cities that follow the religion" },
  TITHE:   { name: "Tithe",          desc: "+1 gold each turn for every city in the world following your religion" },
  ZEAL:    { name: "Holy Warriors",  desc: "+15% combat strength within 2 tiles of a city following your religion" },
};

const RELIGION_FOUND_COST = (nFounded) => 120 + 140 * nFounded;
const MAX_RELIGIONS = 4;
const MISSIONARY_PRESSURE = 150;

// ------------------------------------------------------------
// City-states (independent one-city minors)
// ------------------------------------------------------------
const MINOR_TYPES = {
  mercantile:   { name: "Mercantile",   icon: "💰", desc: "Ally: +4 gold per turn (friend: +2)" },
  maritime:     { name: "Maritime",     icon: "🌾", desc: "Ally: +3 food in your capital (friend: +1)" },
  cultured:     { name: "Cultured",     icon: "🎭", desc: "Ally: +4 culture in your capital (friend: +2)" },
  militaristic: { name: "Militaristic", icon: "⚔️", desc: "Ally: gifts you a unit every 15 turns" },
};

const MINORS = {
  RAGUSA:     { name: "Ragusa",     type: "mercantile",   color: "#7f8c8d", color2: "#ecf0f1", cities: ["Ragusa"] },
  KOTOR:      { name: "Kotor",      type: "maritime",     color: "#5d6d7e", color2: "#aeb6bf", cities: ["Kotor"] },
  IOANNINA:   { name: "Ioannina",   type: "cultured",     color: "#6c7a89", color2: "#d0d3d4", cities: ["Ioannina"] },
  MONEMVASIA: { name: "Monemvasia", type: "maritime",     color: "#616a6b", color2: "#f4f6f6", cities: ["Monemvasia"] },
  BRASOV:     { name: "Brașov",     type: "militaristic", color: "#707b7c", color2: "#e5e8e8", cities: ["Brașov"] },
  RHODES:     { name: "Rhodes",     type: "militaristic", color: "#839192", color2: "#fdfefe", cities: ["Rhodes"] },
};
// City-states are looked up through CIVS as well
for (const [id, m] of Object.entries(MINORS)) {
  CIVS[id] = { name: m.name, leader: m.name, adj: m.name, color: m.color, color2: m.color2,
    trait: MINOR_TYPES[m.type].name + " City-State", traitDesc: MINOR_TYPES[m.type].desc,
    cities: m.cities, minor: true, minorType: m.type };
}

// The barbarian horde — hostile to everyone, wins nothing
CIVS.BARBARIANS = { name: "Barbarians", leader: "—", adj: "Barbarian",
  color: "#3d3d3d", color2: "#b03a2e", cities: [], barb: true,
  trait: "", traitDesc: "" };

const BARB = {
  campEvery: 60,        // 1 camp per ~60 land tiles
  spawnEvery: 9,        // turns between spawns per camp
  maxPerCamp: 2,        // unit cap = camps * maxPerCamp + 2
  clearReward: 40,      // gold for burning a camp
  newCampEvery: 22,     // a new camp may appear this often (up to the initial count)
};

const RUIN_REWARDS = ["gold", "faith", "science", "xp", "map"];

// ------------------------------------------------------------
// Trade routes
// ------------------------------------------------------------
const TRADE = {
  maxRoutes: 3,        // active routes per player
  duration: 40,        // turns before a route expires
  maxDist: 14,         // hex distance limit
  plunderGold: 30,     // reward for plundering a route
};

// ------------------------------------------------------------
// Great People
// ------------------------------------------------------------
const GP = {
  threshold: (n) => 100 + 120 * n,  // points for the (n+1)th great person of a type
  generalAura: 0.15,                // combat bonus near a Great General
  engineerRush: 300,                // production from a Great Engineer
  killPts: 8,                       // general points per kill
};
const GP_NAMES = {
  sci: ["Ruđer Bošković", "Milutin Milanković", "Nikola Tesla", "Mihailo Petrović", "Marin Getaldić", "John Vladislav the Scholar"],
  eng: ["Mimar Hajrudin", "Mihajlo Pupin", "Apollodorus of Damascus", "Petar Bojović", "Master Rade of Studenica"],
  gen: ["Miloš Obilić", "Marko Kraljević", "Ivac the Voivode", "Krum's Champion", "Đurađ Kastriot"],
};

// ------------------------------------------------------------
// Game speeds (tech pace + game length; production is untouched)
// ------------------------------------------------------------
const SPEEDS = {
  quick:    { label: "Quick",    tech: 0.66, turns: 200 },
  standard: { label: "Standard", tech: 1,    turns: 300 },
  epic:     { label: "Epic",     tech: 1.5,  turns: 450 },
};

const INFLUENCE_FRIEND = 30;
const INFLUENCE_ALLY = 60;

// ------------------------------------------------------------
// Espionage — spies unlock with Civil Service, Education, Gunpowder
// ------------------------------------------------------------
const SPY_TECHS = ["CIVIL_SERVICE", "EDUCATION", "GUNPOWDER"];
const SPY_NAMES = ["Miloš", "Jelena", "Petar", "Teodora", "Marko", "Ana", "Stefan", "Mara",
  "Dimitar", "Zora", "Luka", "Irina", "Vuk", "Elena", "Niko", "Ružica"];
const SPY = {
  stealRate: 12,        // progress per turn toward a steal (100 completes)
  stealThreshold: 100,
  catchBase: 0.2,       // chance to be caught on completion
  catchDefended: 0.5,   // ...when a counterspy guards the city
  deadTurns: 15,        // turns to train a replacement
  rigPerTurn: 2,        // influence per turn when rigging a city-state
};

// ------------------------------------------------------------
// Campaign scenarios — fixed matchups with special victory rules
// ------------------------------------------------------------
const SCENARIOS = {
  SAMUIL_976: {
    name: "The Rise of Samuil", year: "976 AD", icon: "👑",
    blurb: "The Cometopuli brothers rise in Ohrid while Byzantium reels. Basil II will not forgive rebellion — take Constantinople before the Bulgar-Slayer takes you. Capture the Byzantine capital within 150 turns.",
    playerCiv: "MACEDONIA", opponents: ["BYZANTIUM", "BULGARIA", "SERBIA"],
    seed: 976001, mapType: "peninsula", difficulty: "normal",
    techEra: 1, gold: 300,
    armies: {
      MACEDONIA: ["SAMUIL_GUARD", "SAMUIL_GUARD", "ARCHER", "WORKER"],
      BYZANTIUM: ["SWORDSMAN", "ARCHER", "SETTLER"],
    },
    warsAtStart: [["MACEDONIA", "BYZANTIUM"]],
    victory: { type: "capture", target: "BYZANTIUM", turns: 150,
      winText: "The Empire kneels. Samuil's tsardom stretches from the Adriatic to the Bosphorus.",
      loseText: "Basil II earns his dread name. The captives of Kleidion walk home blind." },
  },
  FALL_1453: {
    name: "The Fall of Constantinople", year: "1453 AD", icon: "🏰",
    blurb: "Mehmed II stands before the Theodosian Walls with the greatest cannons the world has seen. The Queen of Cities must fall. Capture the Byzantine capital within 60 turns.",
    playerCiv: "OTTOMAN", opponents: ["BYZANTIUM", "SERBIA", "BULGARIA"],
    seed: 1453001, mapType: "peninsula", difficulty: "normal",
    techEra: 2, extraTechs: ["GUNPOWDER", "PHYSICS", "EDUCATION"], gold: 700,
    armies: {
      OTTOMAN: ["JANISSARY", "JANISSARY", "TREBUCHET", "TREBUCHET", "KNIGHT", "WORKER"],
      BYZANTIUM: ["LONGSWORD", "CROSSBOW", "CROSSBOW", "PIKEMAN"],
    },
    warsAtStart: [["OTTOMAN", "BYZANTIUM"]],
    victory: { type: "capture", target: "BYZANTIUM", turns: 60,
      winText: "The Walls are breached. An age ends; the Ottoman age begins.",
      loseText: "The Theodosian Walls hold. Byzantium endures another century." },
  },
  DUSHAN_1346: {
    name: "Dušan's Dream", year: "1346 AD", icon: "🌟",
    blurb: "Crowned Tsar of Serbs and Greeks in Skopje, Stefan Dušan looks south with an emperor's hunger. His code is written; now the sword. Hold three imperial capitals — your own and two of your rivals' — within 130 turns.",
    playerCiv: "SERBIA", opponents: ["BYZANTIUM", "BULGARIA", "BOSNIA"],
    seed: 1346001, mapType: "peninsula", difficulty: "normal",
    techEra: 2, gold: 450,
    armies: {
      SERBIA: ["GUSAR", "GUSAR", "CATAPULT", "PIKEMAN", "WORKER"],
      BYZANTIUM: ["PIKEMAN", "CROSSBOW"],
    },
    warsAtStart: [["SERBIA", "BYZANTIUM"]],
    victory: { type: "capitals", count: 3, turns: 130,
      winText: "Three crowns under one sceptre. The Tsar of Serbs and Greeks bows to no one.",
      loseText: "The dream dies on the road to Constantinople, as it did in 1355." },
  },
  SIMEON_893: {
    name: "The Golden Age of Simeon", year: "893 AD", icon: "📚",
    blurb: "From Preslav's scriptoria flows a river of Slavic letters — while Byzantium probes your borders. Prove Bulgaria the light of the age: be the first to master every technology, within 220 turns, with a war at your doorstep.",
    playerCiv: "BULGARIA", opponents: ["BYZANTIUM", "SERBIA", "MACEDONIA"],
    seed: 893001, mapType: "peninsula", difficulty: "normal",
    techEra: 0, gold: 350,
    armies: {
      BULGARIA: ["KONNIK", "KONNIK", "SPEARMAN", "ARCHER", "WORKER"],
      BYZANTIUM: ["SPEARMAN", "ARCHER"],
    },
    warsAtStart: [["BULGARIA", "BYZANTIUM"]],
    victory: { type: "research", turns: 220,
      winText: "Preslav outshines Constantinople. The golden age is written in a script the world will keep.",
      loseText: "The scriptoria fall silent. Others will write the next century." },
  },
  BASIL_1014: {
    name: "The Bulgar-Slayer", year: "1014 AD", icon: "⚔️",
    blurb: "Samuil's tsardom has defied the Empire for forty years. Basil II marches north with the cataphracts to end it — take Ohrid, Samuil's capital, within 100 turns.",
    playerCiv: "BYZANTIUM", opponents: ["MACEDONIA", "BULGARIA", "SERBIA"],
    seed: 1014001, mapType: "peninsula", difficulty: "normal",
    techEra: 1, gold: 550,
    armies: {
      BYZANTIUM: ["CATAPHRACT", "SWORDSMAN", "CATAPULT", "ARCHER", "WORKER"],
      MACEDONIA: ["SAMUIL_GUARD", "SAMUIL_GUARD", "ARCHER"],
    },
    warsAtStart: [["BYZANTIUM", "MACEDONIA"]],
    victory: { type: "capture", target: "MACEDONIA", turns: 100,
      winText: "Ohrid opens its gates. History will remember what you did to the prisoners of Kleidion.",
      loseText: "Samuil holds the mountain passes. The Empire's armies bleed out in the highlands." },
  },
  TOMISLAV_925: {
    name: "The Kingdom Crowned", year: "925 AD", icon: "👑",
    blurb: "On the field of Duvno, Tomislav is crowned first King of Croatia — and Tsar Simeon's Bulgaria, conqueror of all its neighbours, turns west toward you. Survive the Bulgarian storm: hold your capital for 90 turns.",
    playerCiv: "CROATIA", opponents: ["BULGARIA", "BYZANTIUM", "BOSNIA"],
    seed: 925001, mapType: "peninsula", difficulty: "normal",
    techEra: 1, gold: 350,
    armies: {
      CROATIA: ["USKOK", "SPEARMAN", "ARCHER", "GALLEY", "WORKER"],
      BULGARIA: ["KONNIK", "KONNIK", "SPEARMAN", "CATAPULT", "SETTLER"],
    },
    warsAtStart: [["CROATIA", "BULGARIA"]],
    victory: { type: "survive", turns: 90,
      winText: "As in 926 on the Bosnian highlands: the Bulgarian host breaks against the young kingdom.",
      loseText: "The crown of Duvno rolls in the dust. Croatia waits another generation." },
  },
  VLAD_1462: {
    name: "The Night Attack", year: "1462 AD", icon: "🌙",
    blurb: "Mehmed the Conqueror crosses the Danube with the greatest army in Europe. Vlad Drăculea cannot match it in the field — so the field will become a nightmare. Destroy 12 Ottoman units within 80 turns.",
    playerCiv: "WALLACHIA", opponents: ["OTTOMAN", "BULGARIA", "SERBIA"],
    seed: 1462001, mapType: "peninsula", difficulty: "hard",
    techEra: 2, gold: 450,
    armies: {
      WALLACHIA: ["CALARASI", "CALARASI", "CROSSBOW", "CROSSBOW", "PIKEMAN", "WORKER"],
      OTTOMAN: ["JANISSARY", "JANISSARY", "PIKEMAN", "KNIGHT", "CATAPULT", "SETTLER", "SETTLER"],
    },
    warsAtStart: [["WALLACHIA", "OTTOMAN"]],
    victory: { type: "kills", target: "OTTOMAN", count: 12, turns: 80,
      winText: "The Sultan looks upon the forest of the impaled and turns his horse south. Wallachia is a horror no empire will hold.",
      loseText: "The Danube is crossed, Târgoviște burns, and the voivode flees to the mountains." },
  },
  TVRTKO_1377: {
    name: "Tvrtko's Crown", year: "1377 AD", icon: "🏔️",
    blurb: "In the monastery of Mileševa, Tvrtko Kotromanić takes a double crown — Bosnia and Serbia both. Now make the title true: control six cities, by charter or by sword, within 120 turns.",
    playerCiv: "BOSNIA", opponents: ["SERBIA", "CROATIA", "WALLACHIA"],
    seed: 1377001, mapType: "peninsula", difficulty: "normal",
    techEra: 2, gold: 450,
    armies: {
      BOSNIA: ["KRSTJANI", "KRSTJANI", "ARCHER", "SETTLER", "WORKER"],
    },
    warsAtStart: [],
    victory: { type: "cities", count: 6, turns: 120,
      winText: "Six cities answer to Bobovac. The banate is a kingdom, and the kingdom is real.",
      loseText: "The double crown proves too heavy. Bosnia remains a land between empires." },
  },
  SKANDERBEG_1443: {
    name: "Skanderbeg's Rebellion", year: "1443 AD", icon: "🦅",
    blurb: "Gjergj Kastrioti has raised the double eagle over Krujë. The Sultan's armies are coming, year after year. Hold your capital for 100 turns against the Ottoman tide.",
    playerCiv: "ALBANIA", opponents: ["OTTOMAN", "BYZANTIUM", "BOSNIA"],
    seed: 1443001, mapType: "peninsula", difficulty: "hard",
    techEra: 2, gold: 400,
    armies: {
      ALBANIA: ["STRADIOT", "STRADIOT", "PIKEMAN", "CROSSBOW", "CROSSBOW", "WORKER"],
      OTTOMAN: ["PIKEMAN", "PIKEMAN", "KNIGHT", "CATAPULT", "SETTLER", "SETTLER"],
    },
    warsAtStart: [["ALBANIA", "OTTOMAN"]],
    victory: { type: "survive", turns: 100,
      winText: "Twenty-five years, and Krujë never fell. The mountain eagle outlasted the empire.",
      loseText: "Krujë burns. The Albanian highlands fall silent under the crescent." },
  },
};

// Barbarian-free game; players fight each other.
const GAME_DEFAULTS = { mapW: 44, mapH: 34, maxTurns: 300 };

// ------------------------------------------------------------
// Social policies — four Balkan-flavoured branches. Adopting all
// policies in a branch "completes" it; completing three branches
// wins a Cultural Victory in standard games.
// ------------------------------------------------------------
const POLICY_BRANCHES = {
  ZADRUGA: {
    name: "Zadruga", icon: "🏡", blurb: "The family homestead — growth and land",
    finisher: "+1 population in every city, at once",
    policies: {
      HEARTH:    { name: "Hearth",            desc: "+2 food in the capital" },
      ELDERS:    { name: "Council of Elders", desc: "+2 happiness" },
      HOMESTEAD: { name: "Homestead",         desc: "Borders grow 25% faster" },
      HARVEST:   { name: "Harvest Feast",     desc: "+1 food in every city" },
    },
  },
  JUNAK: {
    name: "Junak", icon: "🗡️", blurb: "The hero's path — war and glory",
    finisher: "+8 gold for every enemy unit slain",
    policies: {
      WARRIOR_CULT: { name: "Warrior Cult",  desc: "+10% strength when attacking" },
      BROTHERHOOD:  { name: "Brotherhood",   desc: "Units heal +5 HP per turn" },
      FRONTIERSMEN: { name: "Frontiersmen",  desc: "4 more maintenance-free units" },
      GUSLARS:      { name: "Guslars",       desc: "+25% strength against barbarians" },
    },
  },
  CARSIJA: {
    name: "Čaršija", icon: "🪙", blurb: "The bazaar quarter — trade and coin",
    finisher: "+2 gold in every city",
    policies: {
      BAZAAR:       { name: "Grand Bazaar",  desc: "+25% gold in the capital" },
      CARAVANSERAI: { name: "Caravanserai",  desc: "+1 trade route" },
      GUILDS:       { name: "Guilds",        desc: "+1 gold per luxury you control" },
      MINTERS:      { name: "Minters",       desc: "Buying in cities costs 15% less" },
    },
  },
  SABOR: {
    name: "Sabor", icon: "⛪", blurb: "The church council — faith and art",
    finisher: "Great People arrive 20% sooner",
    policies: {
      ICONS:    { name: "Icon Painters", desc: "+1 faith in every city" },
      FRESCOES: { name: "Frescoes",      desc: "+2 culture in every city" },
      SYNOD:    { name: "Synod",         desc: "Missionaries cost 25% less faith" },
      PILGRIMS: { name: "Pilgrims",      desc: "+2 happiness" },
    },
  },
};
const POLICY_COST = (adopted) => Math.floor(37 * Math.pow(adopted + 1, 1.68));
const CULTURE_VICTORY_BRANCHES = 3;

// ------------------------------------------------------------
// Unit promotions — chosen on level-up
// ------------------------------------------------------------
const PROMOS = {
  MIGHT:      { name: "Might",       icon: "⚔️", desc: "+15% strength when attacking" },
  BULWARK:    { name: "Bulwark",     icon: "🛡️", desc: "+15% strength when defending" },
  MEDIC:      { name: "Field Medic", icon: "💊", desc: "Heals +5 HP per turn, nearby friends +3" },
  PATHFINDER: { name: "Pathfinder",  icon: "🥾", desc: "Moves through forest and hills without slowing" },
};

// ------------------------------------------------------------
// Diplomacy deals
// ------------------------------------------------------------
const DIPLO = {
  luxuryDealTurns: 30,   // length of a luxury exchange
  giftGold: 100,         // lump-sum gift size
  giftAttitude: 15,      // attitude gained by the recipient
  pactThreshold: 25,     // attitude needed for a defensive pact
  attitudeDecay: 0.5,    // per-turn drift toward neutral
};

// ------------------------------------------------------------
// City-state quests
// ------------------------------------------------------------
const QUESTS = {
  everyTurns: 25,        // a new quest roughly this often per minor
  duration: 25,          // turns before a quest expires
  reward: 30,            // influence for completing one
  killCount: 3,          // barbarians to slay for KILL_BARBS
};

// ------------------------------------------------------------
// Random events — periodic flavour with real mechanical bite.
// kind: "good" | "bad" | "neutral". weight biases how often each fires.
// Effects live in Game.applyEvent(); this table is content + balance.
// ------------------------------------------------------------
const RANDOM_EVENTS = {
  HARVEST:     { name: "Bumper Harvest",       icon: "🌾", kind: "good", weight: 10, needsCity: true },
  MIGRATION:   { name: "Migrants Arrive",      icon: "🧳", kind: "good", weight: 8,  needsCity: true },
  RELICS:      { name: "Sacred Relics Found",  icon: "🕯️", kind: "good", weight: 7,  needsCity: true },
  SCHOLARS:    { name: "Wandering Scholars",   icon: "📜", kind: "good", weight: 7,  needsCity: true },
  TRADE_WINDS: { name: "Favourable Trade",     icon: "💰", kind: "good", weight: 9 },
  FESTIVAL:    { name: "Spontaneous Festival", icon: "🎉", kind: "good", weight: 6 },
  PLAGUE:      { name: "Plague",               icon: "🤢", kind: "bad",  weight: 8,  needsCity: true, minTurn: 20 },
  UNREST:      { name: "Civil Unrest",         icon: "😠", kind: "bad",  weight: 7,  minTurn: 20 },
  FIRE:        { name: "Great Fire",           icon: "🔥", kind: "bad",  weight: 5,  needsCity: true, minTurn: 25 },
  RAIDERS:     { name: "Brigands on the Roads", icon: "🗡️", kind: "bad", weight: 6,  minTurn: 15 },
  DROUGHT:     { name: "Drought",              icon: "🏜️", kind: "bad",  weight: 5,  needsCity: true, minTurn: 25 },
};
const EVENTS = {
  chancePerTurn: 0.10,   // per living major, per turn
  graceTurns: 8,         // no events before this turn
  cooldown: 6,           // min turns between a player's events
};
