"""Extra questions that bring the original demo exams up to 20 questions each.

The seven exams created by seed_demo carry only five questions. TOPUP maps each
of those exam codes to fifteen further questions on the same subject, chosen not
to repeat either the five already on the paper or the course paper in
_exam_bank.py.

Format matches _exam_bank.QUESTIONS:

    (text, option1, option2, option3, option4, correct_option)

with correct_option 1-based.
"""

TOPUP = {}

TOPUP["PHY-MID-01"] = [
    ("Displacement is best described as", "The shortest distance with direction", "The total path length", "The average speed", "The time taken", 1),
    ("Which of these is a scalar quantity?", "Distance", "Force", "Acceleration", "Displacement", 1),
    ("Ignoring air resistance, all bodies in free fall share the same", "Acceleration", "Mass", "Momentum", "Weight", 1),
    ("Mass differs from weight because mass is", "Independent of gravity", "Measured in newtons", "A vector", "Always changing", 1),
    ("The inertia of a body depends on its", "Mass", "Volume", "Shape", "Colour", 1),
    ("Pressure is force divided by", "Area", "Volume", "Time", "Mass", 1),
    ("Density is mass divided by", "Volume", "Area", "Time", "Force", 1),
    ("The time period of a simple pendulum depends on its", "Length", "Mass", "Colour", "Amplitude of swing", 1),
    ("Uniform circular motion always involves a change in", "Direction of velocity", "Speed", "Mass", "Radius", 1),
    ("Ignoring air resistance, a projectile follows a", "Parabola", "Straight line", "Circle", "Spiral", 1),
    ("The area under a velocity time graph gives", "Displacement", "Acceleration", "Force", "Mass", 1),
    ("The slope of a distance time graph gives", "Speed", "Acceleration", "Force", "Energy", 1),
    ("The total momentum of an isolated system is", "Conserved", "Always zero", "Always increasing", "Always decreasing", 1),
    ("Friction acting between surfaces already in relative motion is called", "Kinetic friction", "Static friction", "Rolling resistance", "Tension", 1),
    ("One newton is the force that gives a 1 kg mass an acceleration of", "1 m/s2", "9.8 m/s2", "10 m/s2", "0.1 m/s2", 1),
]

TOPUP["PHY-UT-02"] = [
    ("The resistance of a uniform conductor increases with its", "Length", "Temperature only", "Colour", "Mass", 1),
    ("The SI unit of potential difference is the", "Volt", "Ampere", "Ohm", "Watt", 1),
    ("In a parallel circuit the total resistance is", "Less than the smallest branch resistance", "The sum of all branches", "Equal to one branch", "Always zero", 1),
    ("Electrical power is measured in", "Watt", "Joule", "Volt", "Ohm", 1),
    ("A fuse is connected so that it is", "In series with the circuit", "In parallel with the load", "Outside the circuit", "Across the supply", 1),
    ("Light changing direction as it passes between two media is called", "Refraction", "Reflection", "Diffraction", "Absorption", 1),
    ("A concave mirror can form", "Both real and virtual images", "Only virtual images", "Only real images", "No images", 1),
    ("White light separating into its colours is called", "Dispersion", "Reflection", "Refraction", "Scattering", 1),
    ("An echo is produced by the", "Reflection of sound", "Refraction of sound", "Absorption of sound", "Diffraction of light", 1),
    ("The pitch of a sound depends on its", "Frequency", "Amplitude", "Speed", "Loudness", 1),
    ("The loudness of a sound depends on its", "Amplitude", "Frequency", "Wavelength", "Phase", 1),
    ("Sound travels fastest through", "Steel", "Air", "Water", "Vacuum", 1),
    ("The angle of incidence is equal to the angle of", "Reflection", "Refraction", "Deviation", "Dispersion", 1),
    ("An electric cell converts chemical energy into", "Electrical energy", "Sound energy", "Nuclear energy", "Light energy only", 1),
    ("A short circuit happens when current finds a path of", "Very low resistance", "Very high resistance", "No conductivity", "Infinite impedance", 1),
]

TOPUP["MAT-MID-01"] = [
    ("The highest common factor of 12 and 18 is", "6", "3", "9", "12", 1),
    ("The lowest common multiple of 4 and 6 is", "12", "10", "24", "6", 1),
    ("If 3x = 12 then x equals", "4", "3", "6", "9", 1),
    ("The perimeter of a square of side 5 units is", "20 units", "25 units", "10 units", "15 units", 1),
    ("The interior angles of a quadrilateral add up to", "360 degrees", "180 degrees", "270 degrees", "540 degrees", 1),
    ("The derivative of sin x with respect to x is", "cos x", "-cos x", "sin x", "tan x", 1),
    ("The integral of 2x with respect to x is", "x squared", "2", "x", "2x squared", 1),
    ("tan 45 degrees equals", "1", "0", "0.5", "Undefined", 1),
    ("The mean of 10, 20 and 30 is", "20", "15", "25", "30", 1),
    ("A number divisible by both 2 and 3 is always divisible by", "6", "5", "8", "9", 1),
    ("The value of 5 factorial is", "120", "25", "60", "720", 1),
    ("The slope of a horizontal line is", "0", "1", "-1", "Undefined", 1),
    ("In a right angled triangle the side opposite the right angle is the", "Hypotenuse", "Base", "Altitude", "Median", 1),
    ("The area of a triangle with base b and height h is", "Half of b times h", "b times h", "Twice b times h", "b plus h", 1),
    ("A quadrilateral has how many diagonals?", "2", "1", "3", "4", 1),
]

TOPUP["CHE-UT-01"] = [
    ("The chemical symbol for potassium is", "K", "P", "Po", "Pt", 1),
    ("The chemical formula of carbon dioxide is", "CO2", "CO", "C2O", "CaO", 1),
    ("Bases turn red litmus paper", "Blue", "Red", "Green", "Colourless", 1),
    ("The atomic number of oxygen is", "8", "6", "16", "4", 1),
    ("Isotopes of an element differ in their number of", "Neutrons", "Protons", "Electrons", "Shells", 1),
    ("The lightest element is", "Hydrogen", "Helium", "Lithium", "Carbon", 1),
    ("A mixture of two or more metals is called", "An alloy", "A compound", "A solution", "An isotope", 1),
    ("Separating liquids by their different boiling points is called", "Distillation", "Filtration", "Sublimation", "Decantation", 1),
    ("Electrons around a nucleus occupy regions called", "Shells", "Nuclei", "Bonds", "Ions", 1),
    ("A catalyst changes the", "Rate of a reaction", "Products formed", "Mass of reactants", "Temperature only", 1),
    ("Neutralisation of an acid by a base produces salt and", "Water", "Hydrogen", "Oxygen", "Carbon dioxide", 1),
    ("Which of these is a physical change?", "Melting of ice", "Burning of paper", "Rusting of iron", "Cooking of food", 1),
    ("Vinegar owes its sourness to", "Acetic acid", "Citric acid", "Sulphuric acid", "Nitric acid", 1),
    ("The state of matter with a fixed volume but no fixed shape is", "Liquid", "Solid", "Gas", "Plasma", 1),
    ("Oxidation involves the loss of", "Electrons", "Protons", "Neutrons", "Mass", 1),
]

TOPUP["BIO-FIN-01"] = [
    ("The functional unit of the kidney is the", "Nephron", "Neuron", "Alveolus", "Villus", 1),
    ("Which vessel carries blood away from the heart?", "Artery", "Vein", "Capillary", "Venule", 1),
    ("The liquid part of blood is called", "Plasma", "Serum only", "Lymph", "Platelets", 1),
    ("The digestion of starch begins in the", "Mouth", "Stomach", "Small intestine", "Liver", 1),
    ("Which part of the brain controls balance and coordination?", "Cerebellum", "Cerebrum", "Medulla", "Hypothalamus", 1),
    ("Plants absorb most of their water through", "Root hairs", "Leaves", "Stem", "Flowers", 1),
    ("The male reproductive part of a flower is the", "Stamen", "Carpel", "Petal", "Sepal", 1),
    ("Bacteria are classified as", "Prokaryotes", "Eukaryotes", "Viruses", "Fungi", 1),
    ("Breaking down glucose to release energy is called", "Respiration", "Photosynthesis", "Transpiration", "Digestion", 1),
    ("Which vitamin is needed for blood clotting?", "Vitamin K", "Vitamin C", "Vitamin A", "Vitamin D", 1),
    ("The human heart has how many chambers?", "Four", "Two", "Three", "Five", 1),
    ("Similar tissues working together form an", "Organ", "Organelle", "Cell", "Atom", 1),
    ("A deficiency of iron in the diet causes", "Anaemia", "Rickets", "Scurvy", "Goitre", 1),
    ("An adult human skeleton has about how many bones?", "206", "106", "306", "406", 1),
    ("The pigment that gives skin its colour is", "Melanin", "Chlorophyll", "Haemoglobin", "Carotene", 1),
]

TOPUP["CSC-QZ-01"] = [
    ("RAM stands for", "Random Access Memory", "Read Access Memory", "Rapid Active Module", "Runtime Allocation Map", 1),
    ("One byte consists of how many bits?", "8", "4", "16", "32", 1),
    ("Which of these is system software?", "Operating system", "Spreadsheet", "Web browser", "Photo editor", 1),
    ("The smallest unit of digital data is a", "Bit", "Byte", "Kilobyte", "Word", 1),
    ("An IDE is used to", "Write and debug code", "Browse the web", "Print documents", "Store backups", 1),
    ("Which shortcut copies the selected text?", "Ctrl + C", "Ctrl + V", "Ctrl + X", "Ctrl + Z", 1),
    ("A URL identifies", "A resource on the web", "A local variable", "A file permission", "A network card", 1),
    ("Which device stores data permanently?", "Hard disk", "RAM", "Cache", "Register", 1),
    ("GUI stands for", "Graphical User Interface", "General Utility Input", "Guided User Instruction", "Global Unique Identifier", 1),
    ("A syntax error is detected", "When the code is compiled or parsed", "Only at runtime", "Never", "Only by the user", 1),
    ("Which number system uses only the digits 0 and 1?", "Binary", "Decimal", "Octal", "Hexadecimal", 1),
    ("A function is used to", "Group reusable code", "Store a single value", "End a program", "Comment out code", 1),
    ("The decimal value of binary 1010 is", "10", "8", "12", "5", 1),
    ("Debugging means", "Finding and fixing errors", "Writing documentation", "Deleting files", "Compiling code", 1),
    ("Open source software allows users to", "View and modify the source code", "Use it without a computer", "Avoid all licences", "Sell it as their own", 1),
]

TOPUP["ENG-UT-01"] = [
    ("The opposite of generous is", "Selfish", "Kind", "Helpful", "Giving", 1),
    ("Which of these words is a verb?", "Run", "Table", "Blue", "Quickly", 1),
    ("The plural of mouse is", "Mice", "Mouses", "Mouse", "Mices", 1),
    ("Every complete sentence must contain a subject and a", "Verb", "Adjective", "Preposition", "Conjunction", 1),
    ("The word the is called a", "Definite article", "Indefinite article", "Pronoun", "Adverb", 1),
    ("Identify the adverb in: He runs quickly.", "quickly", "He", "runs", "None", 1),
    ("Which word is spelt correctly?", "Necessary", "Neccessary", "Necesary", "Necessery", 1),
    ("The idiom once in a blue moon means", "Very rarely", "Every month", "At night only", "Very often", 1),
    ("Change to the plural: This is a box.", "These are boxes", "These is boxes", "This are boxes", "These are box", 1),
    ("A synonym for difficult is", "Hard", "Easy", "Simple", "Plain", 1),
    ("The past participle of write is", "Written", "Wrote", "Writed", "Writing", 1),
    ("Which punctuation mark ends a question?", "Question mark", "Full stop", "Comma", "Colon", 1),
    ("In the phrase under the table, under is a", "Preposition", "Verb", "Noun", "Adverb", 1),
    ("The comparative form of bad is", "Worse", "Badder", "Worst", "More bad", 1),
    ("The collective noun for a group of sheep is a", "Flock", "Herd", "Pack", "Swarm", 1),
]
