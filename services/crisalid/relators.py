from django.db import models
from django.utils.translation import gettext_lazy as _

raw = {
    "http://id.loc.gov/vocabulary/relators/fmo": {
        "key": "fmo",
        "value": "former owner",
    },
    "http://id.loc.gov/vocabulary/relators/aue": {
        "key": "aue",
        "value": "audio engineer",
    },
    "http://id.loc.gov/vocabulary/relators/dsr": {"key": "dsr", "value": "designer"},
    "http://id.loc.gov/vocabulary/relators/spk": {"key": "spk", "value": "speaker"},
    "http://id.loc.gov/vocabulary/relators/bpd": {
        "key": "bpd",
        "value": "bookplate designer",
    },
    "http://id.loc.gov/vocabulary/relators/dis": {"key": "dis", "value": "dissertant"},
    "http://id.loc.gov/vocabulary/relators/prn": {
        "key": "prn",
        "value": "production company",
    },
    "http://id.loc.gov/vocabulary/relators/mus": {"key": "mus", "value": "musician"},
    "http://id.loc.gov/vocabulary/relators/cor": {
        "key": "cor",
        "value": "collection registrar",
    },
    "http://id.loc.gov/vocabulary/relators/bka": {"key": "bka", "value": "book artist"},
    "http://id.loc.gov/vocabulary/relators/rse": {
        "key": "rse",
        "value": "respondent-appellee",
    },
    "http://id.loc.gov/vocabulary/relators/ptf": {"key": "ptf", "value": "plaintiff"},
    "http://id.loc.gov/vocabulary/relators/egr": {"key": "egr", "value": "engraver"},
    "http://id.loc.gov/vocabulary/relators/ccp": {"key": "ccp", "value": "conceptor"},
    "http://id.loc.gov/vocabulary/relators/gis": {
        "key": "gis",
        "value": "geographic information specialist",
    },
    "http://id.loc.gov/vocabulary/relators/prt": {"key": "prt", "value": "printer"},
    "http://id.loc.gov/vocabulary/relators/app": {"key": "app", "value": "applicant"},
    "http://id.loc.gov/vocabulary/relators/cpc": {
        "key": "cpc",
        "value": "copyright claimant",
    },
    "http://id.loc.gov/vocabulary/relators/lil": {"key": "lil", "value": "libelant"},
    "http://id.loc.gov/vocabulary/relators/ape": {"key": "ape", "value": "appellee"},
    "http://id.loc.gov/vocabulary/relators/hnr": {"key": "hnr", "value": "honoree"},
    "http://id.loc.gov/vocabulary/relators/cpt": {
        "key": "cpt",
        "value": "complainant-appellant",
    },
    "http://id.loc.gov/vocabulary/relators/orm": {"key": "orm", "value": "organizer"},
    "http://id.loc.gov/vocabulary/relators/brl": {
        "key": "brl",
        "value": "braille embosser",
    },
    "http://id.loc.gov/vocabulary/relators/adp": {"key": "adp", "value": "adapter"},
    "http://id.loc.gov/vocabulary/relators/win": {
        "key": "win",
        "value": "writer of introduction",
    },
    "http://id.loc.gov/vocabulary/relators/ltg": {
        "key": "ltg",
        "value": "lithographer",
    },
    "http://id.loc.gov/vocabulary/relators/fnd": {"key": "fnd", "value": "funder"},
    "http://id.loc.gov/vocabulary/relators/crr": {"key": "crr", "value": "corrector"},
    "http://id.loc.gov/vocabulary/relators/vac": {"key": "vac", "value": "voice actor"},
    "http://id.loc.gov/vocabulary/relators/wde": {
        "key": "wde",
        "value": "wood engraver",
    },
    "http://id.loc.gov/vocabulary/relators/anm": {"key": "anm", "value": "animator"},
    "http://id.loc.gov/vocabulary/relators/mon": {"key": "mon", "value": "monitor"},
    "http://id.loc.gov/vocabulary/relators/elt": {
        "key": "elt",
        "value": "electrotyper",
    },
    "http://id.loc.gov/vocabulary/relators/asn": {
        "key": "asn",
        "value": "associated name",
    },
    "http://id.loc.gov/vocabulary/relators/tlp": {
        "key": "tlp",
        "value": "television producer",
    },
    "http://id.loc.gov/vocabulary/relators/org": {"key": "org", "value": "originator"},
    "http://id.loc.gov/vocabulary/relators/sgd": {
        "key": "sgd",
        "value": "stage director",
    },
    "http://id.loc.gov/vocabulary/relators/com": {"key": "com", "value": "compiler"},
    "http://id.loc.gov/vocabulary/relators/cre": {"key": "cre", "value": "creator"},
    "http://id.loc.gov/vocabulary/relators/ins": {"key": "ins", "value": "inscriber"},
    "http://id.loc.gov/vocabulary/relators/mfr": {
        "key": "mfr",
        "value": "manufacturer",
    },
    "http://id.loc.gov/vocabulary/relators/mod": {"key": "mod", "value": "moderator"},
    "http://id.loc.gov/vocabulary/relators/cmp": {"key": "cmp", "value": "composer"},
    "http://id.loc.gov/vocabulary/relators/dtc": {
        "key": "dtc",
        "value": "data contributor",
    },
    "http://id.loc.gov/vocabulary/relators/fmd": {
        "key": "fmd",
        "value": "film director",
    },
    "http://id.loc.gov/vocabulary/relators/prc": {
        "key": "prc",
        "value": "process contact",
    },
    "http://id.loc.gov/vocabulary/relators/sce": {"key": "sce", "value": "scenarist"},
    "http://id.loc.gov/vocabulary/relators/cli": {"key": "cli", "value": "client"},
    "http://id.loc.gov/vocabulary/relators/dln": {"key": "dln", "value": "delineator"},
    "http://id.loc.gov/vocabulary/relators/cos": {"key": "cos", "value": "contestant"},
    "http://id.loc.gov/vocabulary/relators/pro": {"key": "pro", "value": "producer"},
    "http://id.loc.gov/vocabulary/relators/tad": {
        "key": "tad",
        "value": "technical advisor",
    },
    "http://id.loc.gov/vocabulary/relators/tyd": {
        "key": "tyd",
        "value": "type designer",
    },
    "http://id.loc.gov/vocabulary/relators/trl": {"key": "trl", "value": "translator"},
    "http://id.loc.gov/vocabulary/relators/pmn": {
        "key": "pmn",
        "value": "production manager",
    },
    "http://id.loc.gov/vocabulary/relators/mtk": {
        "key": "mtk",
        "value": "minute taker",
    },
    "http://id.loc.gov/vocabulary/relators/ann": {"key": "ann", "value": "annotator"},
    "http://id.loc.gov/vocabulary/relators/pbl": {"key": "pbl", "value": "publisher"},
    "http://id.loc.gov/vocabulary/relators/tau": {
        "key": "tau",
        "value": "television writer",
    },
    "http://id.loc.gov/vocabulary/relators/lel": {"key": "lel", "value": "libelee"},
    "http://id.loc.gov/vocabulary/relators/waw": {
        "key": "waw",
        "value": "writer of afterword",
    },
    "http://id.loc.gov/vocabulary/relators/arr": {"key": "arr", "value": "arranger"},
    "http://id.loc.gov/vocabulary/relators/aup": {
        "key": "aup",
        "value": "audio producer",
    },
    "http://id.loc.gov/vocabulary/relators/cst": {
        "key": "cst",
        "value": "costume designer",
    },
    "http://id.loc.gov/vocabulary/relators/enj": {
        "key": "enj",
        "value": "enacting jurisdiction",
    },
    "http://id.loc.gov/vocabulary/relators/mte": {
        "key": "mte",
        "value": "metal engraver",
    },
    "http://id.loc.gov/vocabulary/relators/tld": {
        "key": "tld",
        "value": "television director",
    },
    "http://id.loc.gov/vocabulary/relators/wal": {
        "key": "wal",
        "value": "writer of added lyrics",
    },
    "http://id.loc.gov/vocabulary/relators/cph": {
        "key": "cph",
        "value": "copyright holder",
    },
    "http://id.loc.gov/vocabulary/relators/chr": {
        "key": "chr",
        "value": "choreographer",
    },
    "http://id.loc.gov/vocabulary/relators/lse": {"key": "lse", "value": "licensee"},
    "http://id.loc.gov/vocabulary/relators/mdc": {
        "key": "mdc",
        "value": "metadata contact",
    },
    "http://id.loc.gov/vocabulary/relators/rev": {"key": "rev", "value": "reviewer"},
    "http://id.loc.gov/vocabulary/relators/stl": {"key": "stl", "value": "storyteller"},
    "http://id.loc.gov/vocabulary/relators/clt": {"key": "clt", "value": "collotyper"},
    "http://id.loc.gov/vocabulary/relators/ill": {"key": "ill", "value": "illustrator"},
    "http://id.loc.gov/vocabulary/relators/ivr": {"key": "ivr", "value": "interviewer"},
    "http://id.loc.gov/vocabulary/relators/arc": {"key": "arc", "value": "architect"},
    "http://id.loc.gov/vocabulary/relators/cts": {"key": "cts", "value": "contestee"},
    "http://id.loc.gov/vocabulary/relators/lee": {
        "key": "lee",
        "value": "libelee-appellee",
    },
    "http://id.loc.gov/vocabulary/relators/adi": {
        "key": "adi",
        "value": "art director",
    },
    "http://id.loc.gov/vocabulary/relators/ant": {
        "key": "ant",
        "value": "bibliographic antecedent",
    },
    "http://id.loc.gov/vocabulary/relators/elg": {"key": "elg", "value": "electrician"},
    "http://id.loc.gov/vocabulary/relators/osp": {
        "key": "osp",
        "value": "onscreen presenter",
    },
    "http://id.loc.gov/vocabulary/relators/rcp": {"key": "rcp", "value": "addressee"},
    "http://id.loc.gov/vocabulary/relators/anc": {"key": "anc", "value": "announcer"},
    "http://id.loc.gov/vocabulary/relators/pbd": {
        "key": "pbd",
        "value": "publisher director",
    },
    "http://id.loc.gov/vocabulary/relators/att": {
        "key": "att",
        "value": "attributed name",
    },
    "http://id.loc.gov/vocabulary/relators/drm": {"key": "drm", "value": "draftsman"},
    "http://id.loc.gov/vocabulary/relators/prg": {"key": "prg", "value": "programmer"},
    "http://id.loc.gov/vocabulary/relators/ilu": {"key": "ilu", "value": "illuminator"},
    "http://id.loc.gov/vocabulary/relators/ldr": {
        "key": "ldr",
        "value": "laboratory director",
    },
    "http://id.loc.gov/vocabulary/relators/sde": {
        "key": "sde",
        "value": "sound engineer",
    },
    "http://id.loc.gov/vocabulary/relators/stm": {
        "key": "stm",
        "value": "stage manager",
    },
    "http://id.loc.gov/vocabulary/relators/tlh": {
        "key": "tlh",
        "value": "television host",
    },
    "http://id.loc.gov/vocabulary/relators/sng": {"key": "sng", "value": "singer"},
    "http://id.loc.gov/vocabulary/relators/wam": {
        "key": "wam",
        "value": "writer of accompanying material",
    },
    "http://id.loc.gov/vocabulary/relators/sll": {"key": "sll", "value": "seller"},
    "http://id.loc.gov/vocabulary/relators/rsr": {
        "key": "rsr",
        "value": "restorationist",
    },
    "http://id.loc.gov/vocabulary/relators/abr": {"key": "abr", "value": "abridger"},
    "http://id.loc.gov/vocabulary/relators/dto": {"key": "dto", "value": "dedicator"},
    "http://id.loc.gov/vocabulary/relators/hst": {"key": "hst", "value": "host"},
    "http://id.loc.gov/vocabulary/relators/prm": {"key": "prm", "value": "printmaker"},
    "http://id.loc.gov/vocabulary/relators/rsg": {"key": "rsg", "value": "restager"},
    "http://id.loc.gov/vocabulary/relators/cns": {"key": "cns", "value": "censor"},
    "http://id.loc.gov/vocabulary/relators/rcd": {"key": "rcd", "value": "recordist"},
    "http://id.loc.gov/vocabulary/relators/ctb": {"key": "ctb", "value": "contributor"},
    "http://id.loc.gov/vocabulary/relators/rth": {
        "key": "rth",
        "value": "research team head",
    },
    "http://id.loc.gov/vocabulary/relators/pat": {"key": "pat", "value": "patron"},
    "http://id.loc.gov/vocabulary/relators/aud": {
        "key": "aud",
        "value": "author of dialog",
    },
    "http://id.loc.gov/vocabulary/relators/srv": {"key": "srv", "value": "surveyor"},
    "http://id.loc.gov/vocabulary/relators/tch": {"key": "tch", "value": "teacher"},
    "http://id.loc.gov/vocabulary/relators/uvp": {
        "key": "uvp",
        "value": "university place",
    },
    "http://id.loc.gov/vocabulary/relators/wpr": {
        "key": "wpr",
        "value": "writer of preface",
    },
    "http://id.loc.gov/vocabulary/relators/wfw": {
        "key": "wfw",
        "value": "writer of foreword",
    },
    "http://id.loc.gov/vocabulary/relators/prs": {
        "key": "prs",
        "value": "production designer",
    },
    "http://id.loc.gov/vocabulary/relators/art": {"key": "art", "value": "artist"},
    "http://id.loc.gov/vocabulary/relators/mcp": {
        "key": "mcp",
        "value": "music copyist",
    },
    "http://id.loc.gov/vocabulary/relators/pan": {"key": "pan", "value": "panelist"},
    "http://id.loc.gov/vocabulary/relators/stg": {"key": "stg", "value": "setting"},
    "http://id.loc.gov/vocabulary/relators/apl": {"key": "apl", "value": "appellant"},
    "http://id.loc.gov/vocabulary/relators/mfp": {
        "key": "mfp",
        "value": "manufacture place",
    },
    "http://id.loc.gov/vocabulary/relators/pte": {
        "key": "pte",
        "value": "plaintiff-appellee",
    },
    "http://id.loc.gov/vocabulary/relators/edm": {
        "key": "edm",
        "value": "editor of moving image work",
    },
    "http://id.loc.gov/vocabulary/relators/act": {"key": "act", "value": "actor"},
    "http://id.loc.gov/vocabulary/relators/wit": {"key": "wit", "value": "witness"},
    "http://id.loc.gov/vocabulary/relators/rpt": {"key": "rpt", "value": "reporter"},
    "http://id.loc.gov/vocabulary/relators/stn": {
        "key": "stn",
        "value": "standards body",
    },
    "http://id.loc.gov/vocabulary/relators/ive": {"key": "ive", "value": "interviewee"},
    "http://id.loc.gov/vocabulary/relators/vfx": {
        "key": "vfx",
        "value": "visual effects provider",
    },
    "http://id.loc.gov/vocabulary/relators/aui": {
        "key": "aui",
        "value": "author of introduction, etc.",
    },
    "http://id.loc.gov/vocabulary/relators/lsa": {
        "key": "lsa",
        "value": "landscape architect",
    },
    "http://id.loc.gov/vocabulary/relators/auc": {"key": "auc", "value": "auctioneer"},
    "http://id.loc.gov/vocabulary/relators/sgn": {"key": "sgn", "value": "signer"},
    "http://id.loc.gov/vocabulary/relators/ctt": {
        "key": "ctt",
        "value": "contestee-appellant",
    },
    "http://id.loc.gov/vocabulary/relators/pdr": {
        "key": "pdr",
        "value": "project director",
    },
    "http://id.loc.gov/vocabulary/relators/cng": {
        "key": "cng",
        "value": "cinematographer",
    },
    "http://id.loc.gov/vocabulary/relators/jud": {"key": "jud", "value": "judge"},
    "http://id.loc.gov/vocabulary/relators/led": {"key": "led", "value": "lead"},
    "http://id.loc.gov/vocabulary/relators/brd": {"key": "brd", "value": "broadcaster"},
    "http://id.loc.gov/vocabulary/relators/col": {"key": "col", "value": "collector"},
    "http://id.loc.gov/vocabulary/relators/dfe": {
        "key": "dfe",
        "value": "defendant-appellee",
    },
    "http://id.loc.gov/vocabulary/relators/own": {"key": "own", "value": "owner"},
    "http://id.loc.gov/vocabulary/relators/cmt": {"key": "cmt", "value": "compositor"},
    "http://id.loc.gov/vocabulary/relators/nrt": {"key": "nrt", "value": "narrator"},
    "http://id.loc.gov/vocabulary/relators/lit": {
        "key": "lit",
        "value": "libelant-appellant",
    },
    "http://id.loc.gov/vocabulary/relators/dnc": {"key": "dnc", "value": "dancer"},
    "http://id.loc.gov/vocabulary/relators/etr": {"key": "etr", "value": "etcher"},
    "http://id.loc.gov/vocabulary/relators/flm": {"key": "flm", "value": "film editor"},
    "http://id.loc.gov/vocabulary/relators/lbt": {"key": "lbt", "value": "librettist"},
    "http://id.loc.gov/vocabulary/relators/rpc": {
        "key": "rpc",
        "value": "radio producer",
    },
    "http://id.loc.gov/vocabulary/relators/exp": {"key": "exp", "value": "expert"},
    "http://id.loc.gov/vocabulary/relators/rce": {
        "key": "rce",
        "value": "recording engineer",
    },
    "http://id.loc.gov/vocabulary/relators/sht": {
        "key": "sht",
        "value": "supporting host",
    },
    "http://id.loc.gov/vocabulary/relators/dte": {"key": "dte", "value": "dedicatee"},
    "http://id.loc.gov/vocabulary/relators/rbr": {"key": "rbr", "value": "rubricator"},
    "http://id.loc.gov/vocabulary/relators/coe": {
        "key": "coe",
        "value": "contestant-appellee",
    },
    "http://id.loc.gov/vocabulary/relators/cou": {
        "key": "cou",
        "value": "court governed",
    },
    "http://id.loc.gov/vocabulary/relators/drt": {"key": "drt", "value": "director"},
    "http://id.loc.gov/vocabulary/relators/pra": {"key": "pra", "value": "praeses"},
    "http://id.loc.gov/vocabulary/relators/aut": {"key": "aut", "value": "author"},
    "http://id.loc.gov/vocabulary/relators/itr": {
        "key": "itr",
        "value": "instrumentalist",
    },
    "http://id.loc.gov/vocabulary/relators/mxe": {
        "key": "mxe",
        "value": "mixing engineer",
    },
    "http://id.loc.gov/vocabulary/relators/dbp": {
        "key": "dbp",
        "value": "distribution place",
    },
    "http://id.loc.gov/vocabulary/relators/dgg": {
        "key": "dgg",
        "value": "degree granting institution",
    },
    "http://id.loc.gov/vocabulary/relators/msd": {
        "key": "msd",
        "value": "musical director",
    },
    "http://id.loc.gov/vocabulary/relators/rpy": {
        "key": "rpy",
        "value": "responsible party",
    },
    "http://id.loc.gov/vocabulary/relators/spn": {"key": "spn", "value": "sponsor"},
    "http://id.loc.gov/vocabulary/relators/jug": {
        "key": "jug",
        "value": "jurisdiction governed",
    },
    "http://id.loc.gov/vocabulary/relators/djo": {"key": "djo", "value": "dj"},
    "http://id.loc.gov/vocabulary/relators/csp": {
        "key": "csp",
        "value": "consultant to a project",
    },
    "http://id.loc.gov/vocabulary/relators/rst": {
        "key": "rst",
        "value": "respondent-appellant",
    },
    "http://id.loc.gov/vocabulary/relators/bdd": {
        "key": "bdd",
        "value": "binding designer",
    },
    "http://id.loc.gov/vocabulary/relators/rdd": {
        "key": "rdd",
        "value": "radio director",
    },
    "http://id.loc.gov/vocabulary/relators/cur": {"key": "cur", "value": "curator"},
    "http://id.loc.gov/vocabulary/relators/mup": {
        "key": "mup",
        "value": "music programmer",
    },
    "http://id.loc.gov/vocabulary/relators/edd": {
        "key": "edd",
        "value": "editorial director",
    },
    "http://id.loc.gov/vocabulary/relators/cpl": {"key": "cpl", "value": "complainant"},
    "http://id.loc.gov/vocabulary/relators/bkd": {
        "key": "bkd",
        "value": "book designer",
    },
    "http://id.loc.gov/vocabulary/relators/len": {"key": "len", "value": "lender"},
    "http://id.loc.gov/vocabulary/relators/ths": {
        "key": "ths",
        "value": "thesis advisor",
    },
    "http://id.loc.gov/vocabulary/relators/wac": {
        "key": "wac",
        "value": "writer of added commentary",
    },
    "http://id.loc.gov/vocabulary/relators/sfx": {
        "key": "sfx",
        "value": "special effects provider",
    },
    "http://id.loc.gov/vocabulary/relators/aft": {
        "key": "aft",
        "value": "author of afterword, colophon, etc.",
    },
    "http://id.loc.gov/vocabulary/relators/cwt": {
        "key": "cwt",
        "value": "commentator for written text",
    },
    "http://id.loc.gov/vocabulary/relators/let": {
        "key": "let",
        "value": "libelee-appellant",
    },
    "http://id.loc.gov/vocabulary/relators/pad": {
        "key": "pad",
        "value": "place of address",
    },
    "http://id.loc.gov/vocabulary/relators/pfr": {"key": "pfr", "value": "proofreader"},
    "http://id.loc.gov/vocabulary/relators/clr": {"key": "clr", "value": "colorist"},
    "http://id.loc.gov/vocabulary/relators/aqt": {
        "key": "aqt",
        "value": "author in quotations or text abstracts",
    },
    "http://id.loc.gov/vocabulary/relators/dgs": {
        "key": "dgs",
        "value": "degree supervisor",
    },
    "http://id.loc.gov/vocabulary/relators/bnd": {"key": "bnd", "value": "binder"},
    "http://id.loc.gov/vocabulary/relators/lyr": {"key": "lyr", "value": "lyricist"},
    "http://id.loc.gov/vocabulary/relators/ren": {"key": "ren", "value": "renderer"},
    "http://id.loc.gov/vocabulary/relators/spy": {
        "key": "spy",
        "value": "second party",
    },
    "http://id.loc.gov/vocabulary/relators/mrk": {
        "key": "mrk",
        "value": "markup editor",
    },
    "http://id.loc.gov/vocabulary/relators/dfd": {"key": "dfd", "value": "defendant"},
    "http://id.loc.gov/vocabulary/relators/prf": {"key": "prf", "value": "performer"},
    "http://id.loc.gov/vocabulary/relators/ato": {"key": "ato", "value": "autographer"},
    "http://id.loc.gov/vocabulary/relators/his": {
        "key": "his",
        "value": "host institution",
    },
    "http://id.loc.gov/vocabulary/relators/dub": {
        "key": "dub",
        "value": "dubious author",
    },
    "http://id.loc.gov/vocabulary/relators/fon": {"key": "fon", "value": "founder"},
    "http://id.loc.gov/vocabulary/relators/std": {
        "key": "std",
        "value": "set designer",
    },
    "http://id.loc.gov/vocabulary/relators/pth": {
        "key": "pth",
        "value": "patent holder",
    },
    "http://id.loc.gov/vocabulary/relators/tcd": {
        "key": "tcd",
        "value": "technical director",
    },
    "http://id.loc.gov/vocabulary/relators/inv": {"key": "inv", "value": "inventor"},
    "http://id.loc.gov/vocabulary/relators/tyg": {"key": "tyg", "value": "typographer"},
    "http://id.loc.gov/vocabulary/relators/asg": {"key": "asg", "value": "assignee"},
    "http://id.loc.gov/vocabulary/relators/cop": {
        "key": "cop",
        "value": "camera operator",
    },
    "http://id.loc.gov/vocabulary/relators/wat": {
        "key": "wat",
        "value": "writer of added text",
    },
    "http://id.loc.gov/vocabulary/relators/aus": {
        "key": "aus",
        "value": "screenwriter",
    },
    "http://id.loc.gov/vocabulary/relators/cmm": {"key": "cmm", "value": "commentator"},
    "http://id.loc.gov/vocabulary/relators/ard": {
        "key": "ard",
        "value": "artistic director",
    },
    "http://id.loc.gov/vocabulary/relators/bsl": {"key": "bsl", "value": "bookseller"},
    "http://id.loc.gov/vocabulary/relators/edt": {"key": "edt", "value": "editor"},
    "http://id.loc.gov/vocabulary/relators/bkp": {
        "key": "bkp",
        "value": "book producer",
    },
    "http://id.loc.gov/vocabulary/relators/cll": {
        "key": "cll",
        "value": "calligrapher",
    },
    "http://id.loc.gov/vocabulary/relators/ctg": {
        "key": "ctg",
        "value": "cartographer",
    },
    "http://id.loc.gov/vocabulary/relators/ptt": {
        "key": "ptt",
        "value": "plaintiff-appellant",
    },
    "http://id.loc.gov/vocabulary/relators/rtm": {
        "key": "rtm",
        "value": "research team member",
    },
    "http://id.loc.gov/vocabulary/relators/vdg": {
        "key": "vdg",
        "value": "videographer",
    },
    "http://id.loc.gov/vocabulary/relators/wdc": {"key": "wdc", "value": "woodcutter"},
    "http://id.loc.gov/vocabulary/relators/eng": {"key": "eng", "value": "engineer"},
    "http://id.loc.gov/vocabulary/relators/mka": {
        "key": "mka",
        "value": "makeup artist",
    },
    "http://id.loc.gov/vocabulary/relators/ctr": {"key": "ctr", "value": "contractor"},
    "http://id.loc.gov/vocabulary/relators/res": {"key": "res", "value": "researcher"},
    "http://id.loc.gov/vocabulary/relators/cad": {
        "key": "cad",
        "value": "casting director",
    },
    "http://id.loc.gov/vocabulary/relators/cov": {
        "key": "cov",
        "value": "cover designer",
    },
    "http://id.loc.gov/vocabulary/relators/frg": {"key": "frg", "value": "forger"},
    "http://id.loc.gov/vocabulary/relators/trc": {"key": "trc", "value": "transcriber"},
    "http://id.loc.gov/vocabulary/relators/cpe": {
        "key": "cpe",
        "value": "complainant-appellee",
    },
    "http://id.loc.gov/vocabulary/relators/ink": {"key": "ink", "value": "inker"},
    "http://id.loc.gov/vocabulary/relators/tlg": {
        "key": "tlg",
        "value": "television guest",
    },
    "http://id.loc.gov/vocabulary/relators/pop": {
        "key": "pop",
        "value": "printer of plates",
    },
    "http://id.loc.gov/vocabulary/relators/dbd": {
        "key": "dbd",
        "value": "dubbing director",
    },
    "http://id.loc.gov/vocabulary/relators/pnc": {"key": "pnc", "value": "penciller"},
    "http://id.loc.gov/vocabulary/relators/rps": {"key": "rps", "value": "repository"},
    "http://id.loc.gov/vocabulary/relators/fds": {
        "key": "fds",
        "value": "film distributor",
    },
    "http://id.loc.gov/vocabulary/relators/lso": {"key": "lso", "value": "licensor"},
    "http://id.loc.gov/vocabulary/relators/red": {"key": "red", "value": "redaktor"},
    "http://id.loc.gov/vocabulary/relators/dgc": {
        "key": "dgc",
        "value": "degree committee member",
    },
    "http://id.loc.gov/vocabulary/relators/ppt": {"key": "ppt", "value": "puppeteer"},
    "http://id.loc.gov/vocabulary/relators/str": {"key": "str", "value": "stereotyper"},
    "http://id.loc.gov/vocabulary/relators/dft": {
        "key": "dft",
        "value": "defendant-appellant",
    },
    "http://id.loc.gov/vocabulary/relators/crp": {
        "key": "crp",
        "value": "correspondent",
    },
    "http://id.loc.gov/vocabulary/relators/isb": {
        "key": "isb",
        "value": "issuing body",
    },
    "http://id.loc.gov/vocabulary/relators/rap": {"key": "rap", "value": "rapporteur"},
    "http://id.loc.gov/vocabulary/relators/con": {"key": "con", "value": "conservator"},
    "http://id.loc.gov/vocabulary/relators/wst": {
        "key": "wst",
        "value": "writer of supplementary textual content",
    },
    "http://id.loc.gov/vocabulary/relators/scr": {"key": "scr", "value": "scribe"},
    "http://id.loc.gov/vocabulary/relators/acp": {"key": "acp", "value": "art copyist"},
    "http://id.loc.gov/vocabulary/relators/swd": {
        "key": "swd",
        "value": "software developer",
    },
    "http://id.loc.gov/vocabulary/relators/voc": {"key": "voc", "value": "vocalist"},
    "http://id.loc.gov/vocabulary/relators/lbr": {"key": "lbr", "value": "laboratory"},
    "http://id.loc.gov/vocabulary/relators/csl": {"key": "csl", "value": "consultant"},
    "http://id.loc.gov/vocabulary/relators/sad": {
        "key": "sad",
        "value": "scientific advisor",
    },
    "http://id.loc.gov/vocabulary/relators/dpt": {"key": "dpt", "value": "depositor"},
    "http://id.loc.gov/vocabulary/relators/bjd": {
        "key": "bjd",
        "value": "bookjacket designer",
    },
    "http://id.loc.gov/vocabulary/relators/sds": {
        "key": "sds",
        "value": "sound designer",
    },
    "http://id.loc.gov/vocabulary/relators/edc": {
        "key": "edc",
        "value": "editor of compilation",
    },
    "http://id.loc.gov/vocabulary/relators/dpc": {"key": "dpc", "value": "depicted"},
    "http://id.loc.gov/vocabulary/relators/fac": {"key": "fac", "value": "facsimilist"},
    "http://id.loc.gov/vocabulary/relators/blw": {
        "key": "blw",
        "value": "blurb writer",
    },
    "http://id.loc.gov/vocabulary/relators/dst": {"key": "dst", "value": "distributor"},
    "http://id.loc.gov/vocabulary/relators/lie": {
        "key": "lie",
        "value": "libelant-appellee",
    },
    "http://id.loc.gov/vocabulary/relators/cot": {
        "key": "cot",
        "value": "contestant-appellant",
    },
    "http://id.loc.gov/vocabulary/relators/onp": {
        "key": "onp",
        "value": "onscreen participant",
    },
    "http://id.loc.gov/vocabulary/relators/prp": {
        "key": "prp",
        "value": "production place",
    },
    "http://id.loc.gov/vocabulary/relators/scl": {"key": "scl", "value": "sculptor"},
    "http://id.loc.gov/vocabulary/relators/fmp": {
        "key": "fmp",
        "value": "film producer",
    },
    "http://id.loc.gov/vocabulary/relators/cas": {"key": "cas", "value": "caster"},
    "http://id.loc.gov/vocabulary/relators/sec": {"key": "sec", "value": "secretary"},
    "http://id.loc.gov/vocabulary/relators/wft": {
        "key": "wft",
        "value": "writer of intertitles",
    },
    "http://id.loc.gov/vocabulary/relators/wts": {
        "key": "wts",
        "value": "writer of television story",
    },
    "http://id.loc.gov/vocabulary/relators/prv": {"key": "prv", "value": "provider"},
    "http://id.loc.gov/vocabulary/relators/oth": {"key": "oth", "value": "other"},
    "http://id.loc.gov/vocabulary/relators/lgd": {
        "key": "lgd",
        "value": "lighting designer",
    },
    "http://id.loc.gov/vocabulary/relators/pup": {
        "key": "pup",
        "value": "publication place",
    },
    "http://id.loc.gov/vocabulary/relators/plt": {"key": "plt", "value": "platemaker"},
    "http://id.loc.gov/vocabulary/relators/mrb": {"key": "mrb", "value": "marbler"},
    "http://id.loc.gov/vocabulary/relators/cte": {
        "key": "cte",
        "value": "contestee-appellee",
    },
    "http://id.loc.gov/vocabulary/relators/fld": {
        "key": "fld",
        "value": "field director",
    },
    "http://id.loc.gov/vocabulary/relators/wfs": {
        "key": "wfs",
        "value": "writer of film story",
    },
    "http://id.loc.gov/vocabulary/relators/anl": {"key": "anl", "value": "analyst"},
    "http://id.loc.gov/vocabulary/relators/opn": {"key": "opn", "value": "opponent"},
    "http://id.loc.gov/vocabulary/relators/pma": {
        "key": "pma",
        "value": "permitting agency",
    },
    "http://id.loc.gov/vocabulary/relators/rxa": {
        "key": "rxa",
        "value": "remix artist",
    },
    "http://id.loc.gov/vocabulary/relators/pht": {
        "key": "pht",
        "value": "photographer",
    },
    "http://id.loc.gov/vocabulary/relators/pre": {"key": "pre", "value": "presenter"},
    "http://id.loc.gov/vocabulary/relators/pta": {
        "key": "pta",
        "value": "patent applicant",
    },
    "http://id.loc.gov/vocabulary/relators/dnr": {"key": "dnr", "value": "donor"},
    "http://id.loc.gov/vocabulary/relators/med": {"key": "med", "value": "medium"},
    "http://id.loc.gov/vocabulary/relators/evp": {"key": "evp", "value": "event place"},
    "http://id.loc.gov/vocabulary/relators/cnd": {"key": "cnd", "value": "conductor"},
    "http://id.loc.gov/vocabulary/relators/gdv": {
        "key": "gdv",
        "value": "game developer",
    },
    "http://id.loc.gov/vocabulary/relators/dtm": {
        "key": "dtm",
        "value": "data manager",
    },
    "http://id.loc.gov/vocabulary/relators/ltr": {"key": "ltr", "value": "letterer"},
    "http://id.loc.gov/vocabulary/relators/ppm": {"key": "ppm", "value": "papermaker"},
    "http://id.loc.gov/vocabulary/relators/fpy": {"key": "fpy", "value": "first party"},
    "http://id.loc.gov/vocabulary/relators/rsp": {"key": "rsp", "value": "respondent"},
    "http://id.loc.gov/vocabulary/relators/crt": {
        "key": "crt",
        "value": "court reporter",
    },
    "http://id.loc.gov/vocabulary/relators/fmk": {"key": "fmk", "value": "filmmaker"},
    "http://id.loc.gov/vocabulary/relators/nan": {"key": "nan", "value": "news anchor"},
    "http://id.loc.gov/vocabulary/relators/prd": {
        "key": "prd",
        "value": "production personnel",
    },
}


class RolesChoices(models.TextChoices):
    """
    values generated from https://id.loc.gov/vocabulary/relators.json
    """

    ABR = "abr", _("abridger")
    ACP = "acp", _("art copyist")
    ACT = "act", _("actor")
    ADI = "adi", _("art director")
    ADP = "adp", _("adapter")
    AFT = "aft", _("author of afterword, colophon, etc.")
    ANC = "anc", _("announcer")
    ANL = "anl", _("analyst")
    ANM = "anm", _("animator")
    ANN = "ann", _("annotator")
    ANT = "ant", _("bibliographic antecedent")
    APE = "ape", _("appellee")
    APL = "apl", _("appellant")
    APP = "app", _("applicant")
    AQT = "aqt", _("author in quotations or text abstracts")
    ARC = "arc", _("architect")
    ARD = "ard", _("artistic director")
    ARR = "arr", _("arranger")
    ART = "art", _("artist")
    ASG = "asg", _("assignee")
    ASN = "asn", _("associated name")
    ATO = "ato", _("autographer")
    ATT = "att", _("attributed name")
    AUC = "auc", _("auctioneer")
    AUD = "aud", _("author of dialog")
    AUE = "aue", _("audio engineer")
    AUI = "aui", _("author of introduction, etc.")
    AUP = "aup", _("audio producer")
    AUS = "aus", _("screenwriter")
    AUT = "aut", _("author")
    BDD = "bdd", _("binding designer")
    BJD = "bjd", _("bookjacket designer")
    BKA = "bka", _("book artist")
    BKD = "bkd", _("book designer")
    BKP = "bkp", _("book producer")
    BLW = "blw", _("blurb writer")
    BND = "bnd", _("binder")
    BPD = "bpd", _("bookplate designer")
    BRD = "brd", _("broadcaster")
    BRL = "brl", _("braille embosser")
    BSL = "bsl", _("bookseller")
    CAD = "cad", _("casting director")
    CAS = "cas", _("caster")
    CCP = "ccp", _("conceptor")
    CHR = "chr", _("choreographer")
    CLI = "cli", _("client")
    CLL = "cll", _("calligrapher")
    CLR = "clr", _("colorist")
    CLT = "clt", _("collotyper")
    CMM = "cmm", _("commentator")
    CMP = "cmp", _("composer")
    CMT = "cmt", _("compositor")
    CND = "cnd", _("conductor")
    CNG = "cng", _("cinematographer")
    CNS = "cns", _("censor")
    COE = "coe", _("contestant-appellee")
    COL = "col", _("collector")
    COM = "com", _("compiler")
    CON = "con", _("conservator")
    COP = "cop", _("camera operator")
    COR = "cor", _("collection registrar")
    COS = "cos", _("contestant")
    COT = "cot", _("contestant-appellant")
    COU = "cou", _("court governed")
    COV = "cov", _("cover designer")
    CPC = "cpc", _("copyright claimant")
    CPE = "cpe", _("complainant-appellee")
    CPH = "cph", _("copyright holder")
    CPL = "cpl", _("complainant")
    CPT = "cpt", _("complainant-appellant")
    CRE = "cre", _("creator")
    CRP = "crp", _("correspondent")
    CRR = "crr", _("corrector")
    CRT = "crt", _("court reporter")
    CSL = "csl", _("consultant")
    CSP = "csp", _("consultant to a project")
    CST = "cst", _("costume designer")
    CTB = "ctb", _("contributor")
    CTE = "cte", _("contestee-appellee")
    CTG = "ctg", _("cartographer")
    CTR = "ctr", _("contractor")
    CTS = "cts", _("contestee")
    CTT = "ctt", _("contestee-appellant")
    CUR = "cur", _("curator")
    CWT = "cwt", _("commentator for written text")
    DBD = "dbd", _("dubbing director")
    DBP = "dbp", _("distribution place")
    DFD = "dfd", _("defendant")
    DFE = "dfe", _("defendant-appellee")
    DFT = "dft", _("defendant-appellant")
    DGC = "dgc", _("degree committee member")
    DGG = "dgg", _("degree granting institution")
    DGS = "dgs", _("degree supervisor")
    DIS = "dis", _("dissertant")
    DJO = "djo", _("dj")
    DLN = "dln", _("delineator")
    DNC = "dnc", _("dancer")
    DNR = "dnr", _("donor")
    DPC = "dpc", _("depicted")
    DPT = "dpt", _("depositor")
    DRM = "drm", _("draftsman")
    DRT = "drt", _("director")
    DSR = "dsr", _("designer")
    DST = "dst", _("distributor")
    DTC = "dtc", _("data contributor")
    DTE = "dte", _("dedicatee")
    DTM = "dtm", _("data manager")
    DTO = "dto", _("dedicator")
    DUB = "dub", _("dubious author")
    EDC = "edc", _("editor of compilation")
    EDD = "edd", _("editorial director")
    EDM = "edm", _("editor of moving image work")
    EDT = "edt", _("editor")
    EGR = "egr", _("engraver")
    ELG = "elg", _("electrician")
    ELT = "elt", _("electrotyper")
    ENG = "eng", _("engineer")
    ENJ = "enj", _("enacting jurisdiction")
    ETR = "etr", _("etcher")
    EVP = "evp", _("event place")
    EXP = "exp", _("expert")
    FAC = "fac", _("facsimilist")
    FDS = "fds", _("film distributor")
    FLD = "fld", _("field director")
    FLM = "flm", _("film editor")
    FMD = "fmd", _("film director")
    FMK = "fmk", _("filmmaker")
    FMO = "fmo", _("former owner")
    FMP = "fmp", _("film producer")
    FND = "fnd", _("funder")
    FON = "fon", _("founder")
    FPY = "fpy", _("first party")
    FRG = "frg", _("forger")
    GDV = "gdv", _("game developer")
    GIS = "gis", _("geographic information specialist")
    HIS = "his", _("host institution")
    HNR = "hnr", _("honoree")
    HST = "hst", _("host")
    ILL = "ill", _("illustrator")
    ILU = "ilu", _("illuminator")
    INK = "ink", _("inker")
    INS = "ins", _("inscriber")
    INV = "inv", _("inventor")
    ISB = "isb", _("issuing body")
    ITR = "itr", _("instrumentalist")
    IVE = "ive", _("interviewee")
    IVR = "ivr", _("interviewer")
    JUD = "jud", _("judge")
    JUG = "jug", _("jurisdiction governed")
    LBR = "lbr", _("laboratory")
    LBT = "lbt", _("librettist")
    LDR = "ldr", _("laboratory director")
    LED = "led", _("lead")
    LEE = "lee", _("libelee-appellee")
    LEL = "lel", _("libelee")
    LEN = "len", _("lender")
    LET = "let", _("libelee-appellant")
    LGD = "lgd", _("lighting designer")
    LIE = "lie", _("libelant-appellee")
    LIL = "lil", _("libelant")
    LIT = "lit", _("libelant-appellant")
    LSA = "lsa", _("landscape architect")
    LSE = "lse", _("licensee")
    LSO = "lso", _("licensor")
    LTG = "ltg", _("lithographer")
    LTR = "ltr", _("letterer")
    LYR = "lyr", _("lyricist")
    MCP = "mcp", _("music copyist")
    MDC = "mdc", _("metadata contact")
    MED = "med", _("medium")
    MFP = "mfp", _("manufacture place")
    MFR = "mfr", _("manufacturer")
    MKA = "mka", _("makeup artist")
    MOD = "mod", _("moderator")
    MON = "mon", _("monitor")
    MRB = "mrb", _("marbler")
    MRK = "mrk", _("markup editor")
    MSD = "msd", _("musical director")
    MTE = "mte", _("metal engraver")
    MTK = "mtk", _("minute taker")
    MUP = "mup", _("music programmer")
    MUS = "mus", _("musician")
    MXE = "mxe", _("mixing engineer")
    NAN = "nan", _("news anchor")
    NRT = "nrt", _("narrator")
    ONP = "onp", _("onscreen participant")
    OPN = "opn", _("opponent")
    ORG = "org", _("originator")
    ORM = "orm", _("organizer")
    OSP = "osp", _("onscreen presenter")
    OTH = "oth", _("other")
    OWN = "own", _("owner")
    PAD = "pad", _("place of address")
    PAN = "pan", _("panelist")
    PAT = "pat", _("patron")
    PBD = "pbd", _("publisher director")
    PBL = "pbl", _("publisher")
    PDR = "pdr", _("project director")
    PFR = "pfr", _("proofreader")
    PHT = "pht", _("photographer")
    PLT = "plt", _("platemaker")
    PMA = "pma", _("permitting agency")
    PMN = "pmn", _("production manager")
    PNC = "pnc", _("penciller")
    POP = "pop", _("printer of plates")
    PPM = "ppm", _("papermaker")
    PPT = "ppt", _("puppeteer")
    PRA = "pra", _("praeses")
    PRC = "prc", _("process contact")
    PRD = "prd", _("production personnel")
    PRE = "pre", _("presenter")
    PRF = "prf", _("performer")
    PRG = "prg", _("programmer")
    PRM = "prm", _("printmaker")
    PRN = "prn", _("production company")
    PRO = "pro", _("producer")
    PRP = "prp", _("production place")
    PRS = "prs", _("production designer")
    PRT = "prt", _("printer")
    PRV = "prv", _("provider")
    PTA = "pta", _("patent applicant")
    PTE = "pte", _("plaintiff-appellee")
    PTF = "ptf", _("plaintiff")
    PTH = "pth", _("patent holder")
    PTT = "ptt", _("plaintiff-appellant")
    PUP = "pup", _("publication place")
    RAP = "rap", _("rapporteur")
    RBR = "rbr", _("rubricator")
    RCD = "rcd", _("recordist")
    RCE = "rce", _("recording engineer")
    RCP = "rcp", _("addressee")
    RDD = "rdd", _("radio director")
    RED = "red", _("redaktor")
    REN = "ren", _("renderer")
    RES = "res", _("researcher")
    REV = "rev", _("reviewer")
    RPC = "rpc", _("radio producer")
    RPS = "rps", _("repository")
    RPT = "rpt", _("reporter")
    RPY = "rpy", _("responsible party")
    RSE = "rse", _("respondent-appellee")
    RSG = "rsg", _("restager")
    RSP = "rsp", _("respondent")
    RSR = "rsr", _("restorationist")
    RST = "rst", _("respondent-appellant")
    RTH = "rth", _("research team head")
    RTM = "rtm", _("research team member")
    RXA = "rxa", _("remix artist")
    SAD = "sad", _("scientific advisor")
    SCE = "sce", _("scenarist")
    SCL = "scl", _("sculptor")
    SCR = "scr", _("scribe")
    SDE = "sde", _("sound engineer")
    SDS = "sds", _("sound designer")
    SEC = "sec", _("secretary")
    SFX = "sfx", _("special effects provider")
    SGD = "sgd", _("stage director")
    SGN = "sgn", _("signer")
    SHT = "sht", _("supporting host")
    SLL = "sll", _("seller")
    SNG = "sng", _("singer")
    SPK = "spk", _("speaker")
    SPN = "spn", _("sponsor")
    SPY = "spy", _("second party")
    SRV = "srv", _("surveyor")
    STD = "std", _("set designer")
    STG = "stg", _("setting")
    STL = "stl", _("storyteller")
    STM = "stm", _("stage manager")
    STN = "stn", _("standards body")
    STR = "str", _("stereotyper")
    SWD = "swd", _("software developer")
    TAD = "tad", _("technical advisor")
    TAU = "tau", _("television writer")
    TCD = "tcd", _("technical director")
    TCH = "tch", _("teacher")
    THS = "ths", _("thesis advisor")
    TLD = "tld", _("television director")
    TLG = "tlg", _("television guest")
    TLH = "tlh", _("television host")
    TLP = "tlp", _("television producer")
    TRC = "trc", _("transcriber")
    TRL = "trl", _("translator")
    TYD = "tyd", _("type designer")
    TYG = "tyg", _("typographer")
    UVP = "uvp", _("university place")
    VAC = "vac", _("voice actor")
    VDG = "vdg", _("videographer")
    VFX = "vfx", _("visual effects provider")
    VOC = "voc", _("vocalist")
    WAC = "wac", _("writer of added commentary")
    WAL = "wal", _("writer of added lyrics")
    WAM = "wam", _("writer of accompanying material")
    WAT = "wat", _("writer of added text")
    WAW = "waw", _("writer of afterword")
    WDC = "wdc", _("woodcutter")
    WDE = "wde", _("wood engraver")
    WFS = "wfs", _("writer of film story")
    WFT = "wft", _("writer of intertitles")
    WFW = "wfw", _("writer of foreword")
    WIN = "win", _("writer of introduction")
    WIT = "wit", _("witness")
    WPR = "wpr", _("writer of preface")
    WST = "wst", _("writer of supplementary textual content")
    WTS = "wts", _("writer of television story")
