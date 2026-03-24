"""
geocode_lookup.py
-----------------
Mapping of biogeographic region codes to the countries that fall within
each region. Used by ocr_traycontext.py to flag mismatches between a
tray-level geocode and a specimen-level country.

Boundaries are deliberately generous — countries that straddle two
regions (e.g., Mexico spans NEA/NEO, Indonesia spans ORI/AUS) appear
in BOTH regions to avoid false-positive flags. The goal is to catch
clearly impossible combinations (Argentina + PAL), not borderline cases.

Drop this file into functions/.
"""

GEOCODE_COUNTRIES = {

    "NEA": {
        "United States", "USA", "U.S.A.", "U.S.", "US",
        "Canada",
        "Mexico",  # northern Mexico is Nearctic for many taxa
        "Bermuda", "Greenland", "Saint Pierre and Miquelon",
    },

    "NEO": {
        "Mexico",  # also in NEA — straddles the boundary
        "Guatemala", "Belize", "Honduras", "El Salvador", "Nicaragua",
        "Costa Rica", "Panama",
        "Colombia", "Venezuela", "Guyana", "Suriname", "French Guiana",
        "Brazil", "Brasil",
        "Ecuador", "Peru", "Bolivia", "Paraguay", "Uruguay",
        "Argentina", "Chile",
        "Cuba", "Jamaica", "Haiti", "Dominican Republic",
        "Puerto Rico", "Trinidad and Tobago", "Trinidad", "Tobago",
        "Bahamas", "Barbados", "Dominica", "Grenada",
        "Saint Lucia", "Saint Vincent", "Antigua", "Martinique",
        "Guadeloupe", "Curacao", "Aruba", "Bonaire",
        "Galapagos", "Falkland Islands",
    },

    "PAL": {
        # Europe
        "United Kingdom", "UK", "England", "Scotland", "Wales", "Ireland",
        "France", "Germany", "Spain", "Portugal", "Italy",
        "Netherlands", "Belgium", "Luxembourg", "Switzerland", "Austria",
        "Poland", "Czech Republic", "Czechia", "Slovakia", "Hungary",
        "Romania", "Bulgaria", "Serbia", "Croatia", "Slovenia",
        "Bosnia", "Bosnia and Herzegovina", "Montenegro",
        "North Macedonia", "Macedonia", "Albania", "Greece", "Cyprus",
        "Denmark", "Norway", "Sweden", "Finland", "Iceland",
        "Estonia", "Latvia", "Lithuania",
        "Belarus", "Ukraine", "Moldova",
        "Malta", "Andorra", "Monaco", "Liechtenstein", "San Marino",
        # Russia & Central Asia
        "Russia", "USSR", "Soviet Union",
        "Kazakhstan", "Uzbekistan", "Turkmenistan", "Kyrgyzstan", "Tajikistan",
        "Georgia", "Armenia", "Azerbaijan",
        # Middle East
        "Turkey", "Iran", "Iraq", "Syria", "Lebanon", "Israel",
        "Palestine", "Jordan", "Saudi Arabia",
        "Yemen", "Oman", "UAE", "United Arab Emirates",
        "Kuwait", "Bahrain", "Qatar",
        "Afghanistan",
        # North Africa
        "Morocco", "Algeria", "Tunisia", "Libya", "Egypt",
        # Temperate/northern Asia
        "Mongolia", "China", "Taiwan",  # China also in ORI
        "Japan", "South Korea", "North Korea", "Korea",
    },

    "AFR": {
        "South Africa", "Namibia", "Botswana", "Zimbabwe", "Mozambique",
        "Zambia", "Malawi", "Tanzania", "Kenya", "Uganda",
        "Rwanda", "Burundi", "Congo", "Democratic Republic of the Congo",
        "DRC", "Republic of the Congo",
        "Cameroon", "Gabon", "Equatorial Guinea",
        "Central African Republic", "Chad", "Niger", "Nigeria",
        "Ghana", "Togo", "Benin", "Burkina Faso", "Mali",
        "Senegal", "Gambia", "Guinea", "Guinea-Bissau", "Sierra Leone",
        "Liberia", "Ivory Coast", "Cote d'Ivoire",
        "Mauritania",
        "Ethiopia", "Eritrea", "Djibouti", "Somalia", "Somaliland",
        "Sudan", "South Sudan",
        "Angola",
        "Madagascar", "Comoros", "Mauritius", "Reunion", "Seychelles",
        "Swaziland", "Eswatini", "Lesotho",
        "Sao Tome and Principe", "Cape Verde",
        "Egypt",  # also in PAL — straddles the boundary
    },

    "ORI": {
        "India", "Sri Lanka", "Bangladesh", "Myanmar", "Burma",
        "Thailand", "Siam",  # historical name
        "Cambodia", "Laos", "Vietnam",
        "Malaysia", "Singapore",
        "Indonesia",  # western Indonesia is ORI, eastern is AUS
        "Borneo",
        "Philippines",
        "Maldives",
        "Andaman Islands", "Nicobar Islands",
        "Pakistan", "Nepal", "Bhutan",  # borderline PAL/ORI
        "China", "Taiwan",  # southern China borderline
    },

    "AUS": {
        "Australia",
        "Papua New Guinea", "PNG",
        "New Zealand",
        "Indonesia",  # eastern Indonesia (Sulawesi, Moluccas, Papua) is AUS
        "New Caledonia",
        "Solomon Islands",
        "Vanuatu",
        "Tasmania",
    },

    "PAC": {
        "Fiji", "Samoa", "American Samoa", "Tonga",
        "Kiribati", "Tuvalu", "Nauru",
        "Marshall Islands", "Micronesia",
        "Palau",
        "French Polynesia", "Tahiti",
        "Cook Islands", "Niue", "Tokelau",
        "Hawaii",  # politically USA, biogeographically Pacific
        "Guam", "Northern Mariana Islands",
        "Wallis and Futuna",
        "Pitcairn Islands", "Easter Island",
    },
}


# Build reverse lookup: lowercase country -> set of valid geocodes
_COUNTRY_TO_GEOCODES = {}
for _code, _countries in GEOCODE_COUNTRIES.items():
    for _country in _countries:
        _key = _country.lower()
        if _key not in _COUNTRY_TO_GEOCODES:
            _COUNTRY_TO_GEOCODES[_key] = set()
        _COUNTRY_TO_GEOCODES[_key].add(_code)


def check_geocode_country(geocode, country):
    """
    Check whether a country is plausible for a given geocode.

    Returns:
        "" if the combination is plausible or if either value is missing.
        A flag string if the combination is implausible.
    """
    if not geocode or not country:
        return ""
    geocode = geocode.strip().upper()
    country_clean = country.strip()

    if geocode in ("UNK", "") or country_clean == "":
        return ""

    if geocode not in GEOCODE_COUNTRIES:
        return ""

    # Check if the country (or any substring match) appears in the geocode's set
    country_lower = country_clean.lower()

    # Direct match
    if country_lower in _COUNTRY_TO_GEOCODES:
        if geocode in _COUNTRY_TO_GEOCODES[country_lower]:
            return ""
        return f"geocode_mismatch: country '{country_clean}' not typical for geocode '{geocode}'"

    # Substring match (e.g. "South Africa" should match "South Africa")
    for known_country, codes in _COUNTRY_TO_GEOCODES.items():
        if known_country in country_lower or country_lower in known_country:
            if geocode in codes:
                return ""

    # No match found — but don't flag if we simply don't recognize the country,
    # since our list isn't exhaustive
    return ""


def check_ambiguous_locality(country, state_province, locality, municipality=""):
    """
    Flag if there's a locality/municipality but no country or state.
    """
    has_country = country and country.strip() != ""
    has_state = state_province and state_province.strip() != ""
    has_locality = (locality and locality.strip() != "") or (municipality and municipality.strip() != "")

    if has_locality and not has_country and not has_state:
        return "ambiguous_locality"
    return ""
