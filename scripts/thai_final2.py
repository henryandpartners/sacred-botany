#!/usr/bin/env python3
# Final Thai-name generator. Real names where known, else clean Thai-script genus name.
import json, re
BASE="/tmp/thai_lookup"
plants=json.load(open(f"{BASE}/plants.json"))

REAL={
 "ayahuasca":"ยาป่า","peyote":"เปโยเต","san_pedro":"ซานเปโดร","iboga":"อีโบกา",
 "kanna":"คานนา","kava":"คาว่า","fly_agaric":"เห็ดอ้ายแมน","psilocybe":"เห็ดขี้ควาย",
 "jurema":"จูเรมา","ololiuqui":"โอลโอลีอุกี","salvia_divinorum":"เซลเวีย",
 "betel_nut":"หมาก","opium_poppy":"ต้นฝิ่น","kratom":"กระท่อม","blue_lotus":"บัวอียิปต์",
 "dream_herb":"เซเลา","dream_root":"ซิลีน","cannabis":"กัญชา","coca":"โคคา",
 "khat":"คัต","tobacco":"ยาสูบ","mandrake":"แมนเดรก","mugwort":"โกฐจุฬาลัมพาไทย",
 "damiana":"ดาเมียนา","harmala":"นัยน์ตาปีศาจ","ephedra":"อีเฟดรา","bissap":"กระเจี๊ยบ",
 "jujube":"พุทราอินเดีย","wormwood":"เวิร์มวูด",
 "acacia_auriculiformis":"กระถินณรงค์","acacia_mangium":"กระถินเทพา",
 "vachellia_nilotica":"ตาตุ่ม","mucuna_pruriens":"หมามุ้ย","arundo_donax":"อ้อ",
 "limonia_acidissima":"มะขวิด","citrus_limon":"เลมอน","citrus_bergamia":"เบอร์แกมอต",
 "mandarin_orange":"ส้ม","citrus_medica":"มะงั่ว","citrus_sinesis":"ส้มจีน",
 "phragmites_australis":"กก","lolium_perenne":"หญ้าไรย์","zanthoxylum_arborescens":"มะแขว่น",
 "passiflora_edulis":"เสาวรส","uncaria_attenuata":"ยาป่า","ailanthus_malabarica":"นากจามปา",
 "papaver_rhoeas":"ดอกป๊อปปี้","tribulus_terrestris":"โคกกระสุน",
 "opuntia_acanthocarpa":"กระบองเพชร","opuntia_basilaris":"กระบองเพชร",
 "cylindropuntia_echinocarpa":"กระบองเพชร","cylindropuntia_spinosior":"กระบองเพชร",
 "echinopsis_pachanoi":"ซานเปโดร","pelecyphora_aselliformis":"แคคตัส",
 "meconopsis_rudis":"ฝิ่นหิมาลัย","meconopsis_horridula":"ฝิ่นหิมาลัย",
 "meconopsis_robusta":"ฝิ่นหิมาลัย","meconopsis_napaulensis":"ฝิ่นหิมาลัย",
 "meconopsis_paniculata":"ฝิ่นหิมาลัย",
 "papaver_paeoniflorum":"ต้นฝิ่น","papaver_setigerum":"ต้นฝิ่น",
 "acacia_pycnantha":"กระถินทอง","acacia_saligna":"กระถินทอง",
 "passiflora_alata":"เสาวรสร","passiflora_caerulea":"เสาวรสร",
 "carex_brevicollis":"หญ้ากก","carex_parva":"หญ้ากก","plectocomiopsis_geminiflora":"หวายกุ้งน้ำพราย","passiflora_foetida":"กะทกรก",
 "hippophae_rhamnoides":"ไฮโพพี","ziziphus":"พุทรา",
 "mimosa_hostilis":"มิโมซา",
}
GENUS={
 "Acacia":"กระถิน","Acaciella":"อะคาซีลลา","Ailanthus":"จามปา","Amanita":"อะมานิตา",
 "Anadenanthera":"จูเรมา","Apocynum":"อะโพคินัม",
 "Araliopsis":"อะราลิโอพิส","Areca":"หมาก","Aspidosperma":"แอสปิโดสเปอมา","Amsonia":"แอมโซเนีย",
 "Banisteriopsis":"ยาป่า","Borreria":"บอเรีย","Burkea":"เบอร์เกีย","Cabi":"คาบี",
 "Calea":"เซเลา","Callaeum":"คัลเลียม","Calligonum":"คัลลิโกนัม","Calycanthus":"คาลิแคนธัส",
 "Carex":"หญ้ากก","Catha":"คัต","Chrysophyllum":"คริโซฟิลลัม","Citrus":"ส้ม",
 "Cylindropuntia":"กระบองเพชร","Delosperma":"เดโลสเปอมา","Desmanthus":"เดสมันธัส",
 "Desmodium":"เดสโมเดียม","Dictyoloma":"ดิกทิโลมา","Diplopterys":"ดิปลอปเทรีส",
 "Dutaillyea":"ดูแตลเลา","Echinopsis":"เอคิโนพีซ","Elaeagnus":"เอลาอากนัส","Ephedra":"อีเฟดรา",
 "Erythroxylum":"โคคา","Euodia":"ยูเดีย","Fagonia":"ฟากอเนีย","Festuca":"เฟสตูกา",
 "Flindersia":"ฟลินเดเรีย","Grewia":"กรูเวีย","Guiera":"กือเเรีย","Gymnacranthera":"จิมนาครันเธอร์รา",
 "Hammada":"ฮามาด้า","Hibiscus":"กระเจี๊ยบ","Hippophae":"ไฮโพพี","Horsfieldia":"ฮอร์สฟิลด์เซียร์",
 "Iryanthera":"อิรันเทียร์","Kochia":"โคเชีย","Leptactinia":"เลปต่กเทียนเนียร์","Lespedeza":"เลสปเดเซีย",
 "Limonia":"มะขวิด","Lolium":"หญ้าไรย์","Lophophora":"เปโยเต","Mandragora":"แมนเดรก",
 "Meconopsis":"ฝิ่น","Mimosa":"มิโมซา","Mitragyna":"กระท่อม","Mucuna":"หมามุ้ย","Nauclea":"แกงแกมัมบา",
 "Nectandra":"เนคตรานดา","Newbouldia":"นิวบาวเดียร์","Nicotiana":"ยาสูบ","Nitraria":"นิทราริเออร์",
 "Nymphaea":"บัว","Ochrosia":"โอครอเซีย","Ophiorrhiza":"ออฟไฟโอริซา","Opuntia":"กระบองเพชร",
 "Osteophloem":"ออสเทโอเฟลม","Papaver":"ฝิ่น","Passiflora":"เสาวรสร","Pauridiantha":"เปาริเดียนธาร์",
 "Pavetta":"พาเวตตา","Peganum":"เพกานัม","Pelecyphora":"เปเลซีโฟรา","Perriera":"เพอเรีย",
 "Petalostylis":"เปตาโลสตีลิส","Phalaris":"ฟาลาริส","Phragmites":"กก","Phyllodium":"ฟิลโลเดียม",
 "Picrasma":"พิคราสมา","Pilocarpus":"พิโลคาร์พัส","Piper":"พริก","Plectocomiopsis":"เพลกโตโคเมีย",
 "Pleiocarpa":"เพลิโอคาร์พา","Prestonia":"เพรสโทเนีย","Prosopis":"โปรโซพิส","Pseudalbizzia":"อัลบิเซีย",
 "Psilocybe":"เห็ดขี้ควาย","Psychotria":"ไซโคทรี","Rivea":"ริเวีย","Salvia":"เซลเวีย","Sceletium":"คานนา",
 "Senegalia":"กระถิน","Shepherdia":"ชีพเพอร์เดีย","Silene":"ซิลีน","Simira":"ซิเมีย","Strychnos":"สตรีนีโคส",
 "Symplocos":"ซินปลอกอส","Tabernanthe":"อีโบกา","Testulea":"เทสตูเลีย","Tetradium":"เตตราเดียม",
 "Tetrapterys":"เตทราพิเทียร์ส","Tribulus":"โคกกระสุน","Turnera":"ดาเมียนา","Uncaria":"ยาป่า",
 "Vachellia":"กระถิน","Vepris":"เวพริส","Vestia":"เวสเทียร์","Virola":"ไวร็อลา","Voacanga":"อีโบกา",
 "Xanthoxylum":"มะแขว่น","Zanthoxylum":"มะแขว่น","Ziziphus":"พุทรา","Zornia":"ซอเนีย","Zygophyllum":"ไซโกฟิลลัม",
}

def genus_of(sci):
    first=re.split(r"[ +/]",sci.strip())[0]
    return first.split()[0]

final={}
for p in plants:
    pid=p["id"]
    if pid in REAL:
        final[pid]=REAL[pid]
    elif p["thai_current"]:
        final[pid]=p["thai_current"]
    else:
        g=genus_of(p["sci"])
        final[pid]=GENUS.get(g, g)

# sanity: ensure all values are Thai or a known roman placeholder
def thaiish(s):
    return any("\u0E00"<=c<="\u0E7F" for c in s)
bad=[(p["id"],final[p["id"]]) for p in plants if not thaiish(final[p["id"]])]
json.dump(final,open(f"{BASE}/final_thai.json","w"),indent=1,ensure_ascii=False)
print("TOTAL",len(final))
print("non-Thai values (genus fallback):",len(bad))
for b in bad: print("  ",b)
# sample review
import itertools
for p in plants[:0]: pass
print("\n--- full table ---")
for p in plants:
    print(f"{p['id']:34s} {p['name'][:26]:26s} => {final[p['id']]}")
