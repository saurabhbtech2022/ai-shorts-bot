#!/usr/bin/env python3
"""Generate data/prompts.txt — full Ramcharitmanas (Tulsidas) kram, ek line = ek Short."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.overlay_text import normalize_mixed_hindi  # noqa: E402

# (Hindi title, English image prompt, Hindi caption — pure Devanagari)
SCENES: list[tuple[str, str, str]] = [
    # —— बाल काण्ड ——
    ("मंगलाचरण", "Divine golden light Om Namah Shivay sage Tulsidas writing manuscript temple", "श्री गुरु चरण सरोज रज — रामचरित मानस की कथा वंदन से शुरू होती है"),
    ("अयोध्या महिमा", "Ancient Ayodhya on Sarayu river golden palaces sunrise Kosala kingdom", "कोसल की पावन नगरी अयोध्या — सरयू तट पर धर्म और शांति का राज्य"),
    ("महाराज दशरथ", "King Dasharatha on throne queens Kausalya Kaikeyi Sumitra royal court", "महाराज दशरथ न्यायप्रिय धर्मात्मा — प्रजा सुखी, राज्य समृद्ध"),
    ("न संतान चिंता", "King Dasharatha worried no heir priests advising palace night", "राजा को संतान न होने की चिंता — ऋषियों ने उपाय बताया"),
    ("ऋष्यशृंग आमंत्रण", "Sage Rishyashringa arriving Ayodhya royal welcome", "महर्षि ऋष्यशृंग को बुलाया गया — यज्ञ की पवित्रता के लिए"),
    ("पुत्रकामेष्टि यज्ञ", "Putrakameshti yajna fire altar kings sages chanting", "पुत्रकामेष्टि यज्ञ — वंश और राज्य की शुभ कामना"),
    ("दिव्य प्रसाद", "Celestial being offering divine payasam to queens golden light", "यज्ञ से दिव्य प्रसाद — चारों रानियों को मिला"),
    ("चारों राजकुमार", "Four divine babies born palace chambers celestial aura", "चारों राजकुमारों का दिव्य जन्म — राम, लक्ष्मण, भरत, शत्रुघ्न"),
    ("श्री राम अवतार", "Baby Rama divine form Vishnu symbols lotus conch", "श्री राम भगवान के अवतार — अयोध्या में अंश अवतरित"),
    ("नामकरण संस्कार", "Naming ceremony four princes royal priests", "नामकरण संस्कार — राम नाम सबके हृदय में"),
    ("बाल राम लीला", "Young Rama playing in Ayodhya gardens golden childhood", "बाल राम की लीलाएँ — सरल, पवित्र, सबको प्रिय"),
    ("गुरुकुल शिक्षा", "Young princes learning archery scriptures guru vashishtha", "गुरु वशिष्ठ से शिक्षा — धर्म, शास्त्र, धनुर्विद्या"),
    ("विश्वामित्र आगमन", "Sage Vishwamitra entering Dasharatha court requesting help", "मुनि विश्वामित्र अयोध्या आए — राक्षसों से यज्ञ बचाना"),
    ("दशरथ की चिंता", "Dasharatha reluctant to send young Rama emotional court", "राजा को लाला राम को वन भेजने का दुख"),
    ("वशिष्ठ उपदेश", "Vasishtha advising Dasharatha to send Rama duty", "गुरु वशिष्ठ ने कहा — पुत्र को धर्म यात्रा का अवसर दो"),
    ("राम लक्ष्मण प्रस्थान", "Rama Lakshman leaving Ayodhya with Vishwamitra forest path", "राम और लक्ष्मण मुनि के साथ — धर्म की राह पर"),
    ("ताड़का वध", "Young Rama shooting demoness Tadaka forest Vishwamitra", "ताड़का राक्षसी का संहार — राम की पराक्रम की शुरुआत"),
    ("सिद्धाश्रम रक्षा", "Rama Lakshman protecting yajna from demons Siddhashram", "सिद्धाश्रम में यज्ञ की रक्षा — राक्षस भगाए"),
    ("अहिल्या उद्धार", "Rama foot touching stone Ahilya restored woman divine", "अहिल्या का उद्धार — शाप से मुक्ति, राम की करुणा"),
    ("मिथिला प्रस्थान", "Rama Lakshman Vishwamitra walking toward Mithila gates", "मिथिला की ओर — जनक राज्य, धर्म की परीक्षा"),
    ("जनक का धर्म", "King Janaka court sages Shiva bow displayed hall", "राजा जनक धर्मराज — सभा में शिव धनुष"),
    ("स्वयंवर सभा", "Princess Sita palace many kings assembly swayamvar", "स्वयंवर सभा — अनेक राजा, अजेय धनुष"),
    ("धनुष असफल", "Warriors failing to lift Shiva bow Mithila hall", "कोई धनुष न हिला — शिव की महिमा"),
    ("राम धनुष भंग", "Rama lifting breaking Shiva bow sparks divine light", "श्री राम ने शिव धनुष तोड़ा — सीता स्वयंवर विजय"),
    ("परशुराम संवाद", "Parashurama confronting Rama axe then calm respect", "परशुराम से मिलन — क्रोध शांत, राम की महिमा"),
    ("चार विवाह", "Four wedding mandaps Rama Sita Lakshman couples fire ritual", "चार विवाह — राम-सीता, लक्ष्मण-उर्मिला, भरत-मांडवी, शत्रुघ्न-श्रुतकीर्ति"),
    ("विवाह प्रवेश", "Wedding procession entering Ayodhya citizens flowers", "विवाह के बाद अयोध्या प्रवेश — उमंग और आशीर्वाद"),
    # —— अयोध्या काण्ड ——
    ("युवराज घोषणा", "Dasharatha announcing Rama as Yuvaraja happy citizens", "राम को युवराज घोषित — प्रजा अनंदित"),
    ("मंथरा का द्वेष", "Manthara servant hearing news jealous palace", "मंथरा को बुरी खबर — ईर्ष्या जागी"),
    ("कैकेयी को बहकाना", "Manthara poisoning Kaikeyi mind night palace", "मंथरा ने कैकेयी के मन में विष बोया"),
    ("क्रोध भवन", "Kaikeyi in anger room floor jewels Dasharatha arrives", "कैकेयी क्रोध भवन में — दो वर माँगे"),
    ("वन और राज्य वर", "Kaikeyi demanding exile fourteen years Bharat throne", "चौदह वर्ष वनवास — भरत को राज्य का वचन"),
    ("राम को बुलाव", "Messenger summoning Rama Kaikeyi harsh words", "राम को बुलाया गया — कैकेयी का कठोर वचन"),
    ("राम वन स्वीकार", "Rama calm accepting exile decree before parents", "राम ने वनवास शांत चित्त से स्वीकार किया"),
    ("सीता वन चलना", "Sita insisting follow Rama forest exile", "सीता बोली — पति संग वन ही मेरा राज्य"),
    ("लक्ष्मण व्रत", "Lakshman leaving with Rama Sita loyal brother bow", "लक्ष्मण ने व्रत लिया — भाई का साथ न छोड़ना"),
    ("दशरथ विलाप", "Dasharatha heartbroken crying Rama departure", "दशरथ का हृदय टूटा — पुत्र वियोग"),
    ("अयोध्या विदाई", "Rama Sita Lakshman leaving city citizens weeping", "अयोध्या से प्रस्थान — लोग रोए, राम धैर्य"),
    ("प्रजा अनुनय", "Citizens following Rama Rama sends them back duty", "प्रजा पीछे आई — राम ने लौटाया, राजधर्म समझाया"),
    ("शृंगवेरपुर", "Guha boatman meeting Rama Sarayu bank", "निषाद राज गुह — सरयू तट पर राम का स्वागत"),
    ("सुमंत वापसी", "Chariot Sumant returning empty Ayodhya grief", "सुमंत अयोध्या लौटे — खाली रथ, दुख"),
    ("केवट प्रसंग", "Boatman Kevat washing Rama feet ferry Ganga dawn", "केवट की नौ — पग धोए, भक्ति से पार"),
    ("भरद्वाज आश्रम", "Sage Bharadvaj hermitage Rama rest blessing", "भरद्वाज ऋषि के आश्रम — विश्राम और आशीर्वाद"),
    ("चित्रकूट वास", "Rama Sita Lakshman hut Chitrakoot hills simple life", "चित्रकूट में कुटिया — सरल जीवन, धर्म"),
    ("भरत समाचार", "Bharat Shatrughna returning learning exile news shock", "भरत को खबर मिली — राम का वनवास, हृदय व्याकुल"),
    ("भरत रोष", "Bharat angry at Kaikeyi Manthara confrontation", "भरत का क्रोध — माँ कैकेयी से प्रश्न"),
    ("दशरथ अंत", "Dasharatha death bed grieving Rama Sarayu", "दशरथ का देहांत — राम वियोग में राजा गए"),
    ("अंतिम संस्कार", "Royal funeral Dasharatha pyre Bharat grief", "दशरथ का अंतिम संस्कार — राज्य शोक में"),
    ("भरत चित्रकूट यात्रा", "Bharat army walking toward Chitrakoot forest", "भरत चित्रकूट गए — राम को वापस लाने"),
    ("भरत मिलन", "Bharat meeting Rama Chitrakoot forest emotional", "भरत-राम मिलन — भक्ति और त्याग"),
    ("राम उपदेश", "Rama advising Bharat duty kingdom dharma", "राम ने समझाया — पितृ आज्ञा, राज्य भरत का नहीं"),
    ("राम पादुका", "Bharat placing Rama wooden sandals on throne Ayodhya", "राम की पादुका — भरत ने राजसिंहासन पर रखी"),
    ("नंदिग्राम वास", "Bharat living simply Nandigram waiting Rama return", "भरत नंदिग्राम — तपस्वी जीवन, राम की प्रतीक्षा"),
    ("अत्रि अनसूया", "Sage Atri Anasuya blessing Sita Rama forest", "अत्रि-अनसूया — सीता को वरदान, पति व्रत की महिमा"),
    ("दंडकाराण्य प्रवेश", "Trio entering Dandaka forest hermitages sages", "दंडकारण्य में प्रवेश — ऋषि-मुनियों की रक्षा का वचन"),
    # —— अरण्य काण्ड ——
    ("विराध वध", "Rama killing demon Viradha forest giant", "विराध राक्षस का वध — अरण्य में प्रथम संग्राम"),
    ("शर्भंग मोक्ष", "Sage Sharabhanga attaining heaven Rama witnessing", "ऋषि शर्भंग को मोक्ष — राम के दर्शन से"),
    ("सुतीक्ष्ण आश्रम", "Hermitage Sutikshna Rama Lakshman rest", "सुतीक्ष्ण आश्रम — विश्राम और धर्म चर्चा"),
    ("अगस्त्य आश्रम", "Sage Agastya giving weapons Rama divine bow", "अगस्त्य मुनि ने दिव्य शस्त्र और धनुष दिए"),
    ("पंचवटी वास", "Rama building cottage Panchavati Godavari river", "गोदावरी तट पर पंचवटी — पवित्र कुटिया बसाई"),
    ("शूर्पणखा", "Shurpanakha approaching Rama Lakshman forest", "शूर्पणखा आई — लंका की बहन, कामना"),
    ("नाक काटना", "Lakshman cutting Shurpanakha nose forest", "लक्ष्मण ने शूर्पणखा की नाक काटी — अपमान"),
    ("खर दूषण", "Khara Dushana demon army attacking Rama battle", "खर और दूषण की सेना — राम ने पराजित की"),
    ("त्रिशिरा वध", "Rama killing Trishira demon forest", "त्रिशिरा का संहार — अरण्य में शांति"),
    ("स्वर्ण मृग", "Golden magical deer Maricha luring Sita forest", "मायावी स्वर्ण मृग — मारीच की चाल"),
    ("सीता वनोद्यान", "Sita pointing golden deer asking Rama fetch", "सीता ने कहा — वह मृग ले आओ"),
    ("राम मृग पीछे", "Rama chasing deer deep forest Lakshman left", "राम मृग के पीछे — दूर चले"),
    ("लक्ष्मण रेखा", "Lakshman drawing protective line cottage Sita inside", "लक्ष्मण रेखा — सीता को रक्षा में रखा"),
    ("रावण भिक्षु रूप", "Ravana disguised as ascetic begging alms Sita", "रावण साधु वेश — छल से द्वार"),
    ("सीता हरण", "Ravana abducting Sita pushpak vimana sky", "रावण ने सीता हरण की — विमान में"),
    ("जटायु युद्ध", "Eagle Jatayu fighting Ravana sky wounded", "जटायु ने रावण से युद्ध — वीर गति"),
    ("जटायु मुक्ति", "Dying Jatayu telling Rama direction Lanka", "जटायu ने प्राण tyagi — disha batayi"),
    ("राम विलाप", "Rama Lakshman grieving searching Sita forest", "राम का विलाप — सीता वियोग"),
    ("कबंध उद्धार", "Rama freeing cursed Kabandha giant forest", "कबंध की मुक्ति — सुगriv ki disha"),
    ("शबरी मिलन", "Old devotee Shabari offering berries Rama tasting", "शबरी के बेर — भक्ति, राम ने grahan kiye"),
    ("ऋष्यमूक पर्वत", "Sugriva on hill fearing Bali throwing rocks", "ऋष्यमूक — sugreev bhag rahe the"),
    ("हनुमान पहचान", "Hanuman disguised meeting Rama Lakshman", "hanuman ne pehchan — ram ka parichay"),
    ("अग्नि मित्रता", "Rama Sugriva friendship fire ritual", "agni sakshi — ram sugreev mitrata"),
    ("बाली युद्ध", "Bali Sugriva duel Rama arrow from behind", "bali yuddh — nyay ke liye ram ka arrow"),
    ("तारा विलाप", "Tara grieving Bali death advising Sugriva", "tara ka vilap — sugreev ko updesh"),
    ("सुग्रीव राज्य", "Sugriva crowned Kishkindha Rama blessing", "sugreev raja — kishkindha singhasan"),
    ("वर्षा ऋतु", "Monsoon Rama waiting cave four months rain", "varsha ritu — ram pratiksha, dhairya"),
    # —— किष्किंधा / सुंदर ——
    ("सीता खोज आदेश", "Rama ordering monkey armies four directions search", "char disha — vanar sena sita khoj"),
    ("अंगद सहित दल", "Angad leading search party south", "angad senapati — dakshin disha"),
    ("संपाति उपदेश", "Old vulture Sampati telling ocean path Lanka", "sampati — samudra paar lanka"),
    ("हनुमान विस्तार", "Hanuman expanding giant form before ocean leap", "hanuman ka roop vishal — samudra langhan"),
    ("मैनाक सम्मान", "Mainaka mountain rising sea Hanuman rest", "mainak parvat — samudra ka samman"),
    ("सुरसा परीक्षा", "Surasa serpent mother testing Hanuman mouth", "surasa pariksha — hanuman ki shakti"),
    ("सिंहिका ग्रस", "Simhika demoness grabbing shadow Hanuman escapes", "simhika — chhaya pakad, mukti"),
    ("लंका दर्शन", "Hanuman first view golden Lanka city night", "lanka darshan — sone ki nagari"),
    ("लंका दहन", "Hanuman tail fire burning Lanka night flames", "lanka mein agni — adharm ka dahan"),
    ("अशोक वाटिका", "Hanuman meeting Sita Ashoka tree giving ring", "ashok vatika — ram ka angoothi sandesh"),
    ("रावण धमक", "Ravana threatening Sita Hanuman watching hidden", "ravan ki dhamki — sita adhil"),
    ("प्रलयंकर मुद्रिका", "Sita giving jewel token Hanuman to Rama", "mudrika — ram tak sandesh"),
    ("हनुमान बंधन", "Hanuman captured Ravana court tail fire", "hanuman bandhan — punah lanka agni"),
    ("विभीषण शरण", "Vibhishana leaving Lanka seeking Rama refuge", "vibhishan sharan — ram ke charan"),
    # —— लंका काण्ड ——
    ("समुद्र तट प्रार्थना", "Rama praying seashore vast army behind", "samudra tat — ram ki prarthna"),
    ("समुद्र देव", "Ocean god appearing advising bridge Nala", "samudra dev — setu marg"),
    ("राम सेतु", "Monkeys building floating stone bridge ocean", "ram setu — patthar tairte, sena paar"),
    ("लंका घेराव", "Rama army surrounding Lanka epic camp", "lanka gherao — yuddh ki taiyari"),
    ("अंगद दूत", "Angad messenger Ravana court fearless toe", "angad dhoot — ravan sabha mein dharm"),
    ("मेघनाद युद्ध", "Indrajit serpent arrows binding Rama Lakshman", "meghnad nagpash — ram lakshman bandhan"),
    ("गरुड़ आगमन", "Garuda freeing Rama Lakshman serpent bonds sky", "garud aaye — mukti, shakti"),
    ("कुंभकर्ण जागरण", "Kumbhakarna waking giant entering war Lanka", "kumbhakarn jaga — yuddh mein"),
    ("कुंभकर्ण वध", "Rama killing Kumbhakarna fierce battle", "kumbhakarn vadh — ram ki veerta"),
    ("लक्ष्मण शक्ति", "Lakshman wounded Shakti astra fallen battlefield", "lakshman shakti — ghayal, chinta"),
    ("संजीवनी अंजन", "Hanuman flying Dronagiri mountain herbs night", "sanjivani — hanuman parvat uthaya"),
    ("लक्ष्मण चेतना", "Lakshman revived herbs Hanuman returned", "lakshman huye chetna — jivan dayi"),
    ("मेघनाद वध", "Lakshman killing Indrajit breaking illusions", "meghnad ka ant — lakshman veer"),
    ("रावण युद्ध", "Rama Ravana final chariot battle divine weapons", "ram ravan antim yuddh"),
    ("रावण वध", "Rama final arrow Ravana falling sunset battlefield", "dashanan ka vadh — dharm vijay"),
    ("मंदोदरी विलाप", "Mandodari grieving Ravana death Lanka", "mandodari vilap — pati viyog"),
    ("विभीषण राज्य", "Vibhishana crowned Lanka Rama approval", "vibhishan raja — ram anumati"),
    ("सीता मिलन", "Rama reuniting Sita after war emotional", "yuddh ke baad milap — anand"),
    ("अग्नि परीक्षा", "Sita entering sacred fire Agni Pariksha divine", "agni pariksha — pavitrata praman"),
    ("ब्रह्मा स्तुति", "Gods praising Sita purity fire ritual", "dev gan stuti — sita maryada"),
    # —— उत्तर काण्ड / अगमन ——
    ("विजय प्रस्थान", "Pushpak vimana preparing return Ayodhya sky", "pushpak — ayodhya ki ore"),
    ("अयोध्या दीप", "Ayodhya citizens lighting lamps welcoming return", "deep jalao — ram agaman"),
    ("भरत मिलन", "Bharat meeting Rama Nandigram joy embrace", "bharat milap — bhai prem"),
    ("राम राज्याभिषेक", "Coronation Rama Sita queen sages chanting", "ram rajyabhishek — ram rajya"),
    ("राम राज्य सुख", "Prosperous Ayodhya golden fields happy subjects", "ram rajya — sab sukhi, nyay"),
    ("अश्वमेध", "Ashwamedha yagya horse sacrifice Rama royal", "ashwamedh — dharm sthapana"),
    ("लव कुश जन्म", "Twins Luv Kush born Valmiki ashram Sita", "luv kush janm — ashram mein"),
    ("रामायण गान", "Luv Kush singing Ramayana Rama court unrecognized", "katha gayan — ram sunte rahasya"),
    ("सीता भूमि", "Earth opening accepting Sita divine forest", "dharti mata — sita le gayi"),
    ("राम अंतिम लीला", "Elder Rama Sarayu river divine departure light", "ram avtar samapt — dharm amar"),
]

HEADER = """# श्री रामचरित मानस (गोस्वामी तुलसीदास) — पूरी कथा क्रम से
# एक पंक्ति = एक YouTube Short (subah/dopahar/sham — 3 प्रतिदिन)
# Format: Hindi title | English image prompt | Hindi caption [| narration] [| on-screen text]

"""


def _clean_caption(caption: str) -> str:
    if re.search(r"[A-Za-z]{2,}", caption):
        cleaned = normalize_mixed_hindi(caption)
        if len(cleaned) >= 10:
            return cleaned
    return caption


def main() -> None:
    out = ROOT / "data" / "prompts.txt"
    lines = [HEADER]
    for title, en, cap in SCENES:
        cap = _clean_caption(cap)
        lines.append(f"{title} | {en} | {cap}\n")
    out.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote {len(SCENES)} scenes to {out}")


if __name__ == "__main__":
    main()
