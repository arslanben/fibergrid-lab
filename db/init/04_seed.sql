-- FiberGrid CTF - synthetic data set (deterministic).
-- All records are fictional. Coordinates are approximate district centres.

-- ---------------------------------------------------------------------------
-- FWA coverage inventory (published layer data, 118,427 records)
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE seed_points AS
SELECT * FROM (VALUES
    (1,  'İSTANBUL',   'KADIKÖY',      'CAFERAĞA',      29.027, 40.992),
    (2,  'İSTANBUL',   'BEŞİKTAŞ',     'LEVENT',        29.013, 41.077),
    (3,  'İSTANBUL',   'ATAŞEHİR',     'İÇERENKÖY',     29.102, 40.987),
    (4,  'İSTANBUL',   'BAKIRKÖY',     'ZUHURATBABA',   28.872, 40.981),
    (5,  'ANKARA',     'ÇANKAYA',      'KIZILAY',       32.859, 39.920),
    (6,  'ANKARA',     'YENİMAHALLE',  'BATIKENT',      32.744, 39.969),
    (7,  'ANKARA',     'KEÇİÖREN',     'ETLİK',         32.825, 39.980),
    (8,  'İZMİR',      'BORNOVA',      'EVKA-3',        27.204, 38.467),
    (9,  'İZMİR',      'KONAK',        'ALSANCAK',      27.140, 38.435),
    (10, 'İZMİR',      'KARŞIYAKA',    'MAVİŞEHİR',     27.090, 38.465),
    (11, 'BURSA',      'NİLÜFER',      'ÖZLÜCE',        28.973, 40.215),
    (12, 'ANTALYA',    'MURATPAŞA',    'LARA',          30.752, 36.850),
    (13, 'ADANA',      'SEYHAN',       'REŞATBEY',      35.322, 37.003),
    (14, 'KONYA',      'SELÇUKLU',     'BOSNA',         32.492, 37.906),
    (15, 'KOCAELİ',    'GEBZE',        'DARICA',        29.431, 40.767),
    (16, 'GAZİANTEP',  'ŞAHİNBEY',     'İNCİLİPINAR',   37.376, 37.061),
    (17, 'KAYSERİ',    'MELİKGAZİ',    'KOCASİNAN',     35.489, 38.731),
    (18, 'MERSİN',     'AKDENİZ',      'MEZİTLİ',       34.632, 36.800),
    (19, 'SAMSUN',     'ATAKUM',       'DENİZEVLERİ',   36.330, 41.286),
    (20, 'TRABZON',    'ORTAHİSAR',    'DEĞİRMENDERE',  39.716, 41.003)
) AS v(pid, il, ilce, mahalle, lon, lat);

INSERT INTO sde.fwa_nokta_verisi (objectid, il, ilce, mahalle, bant, kapasite, durum, lon, lat)
SELECT g,
       p.il,
       p.ilce,
       p.mahalle,
       (ARRAY['3.5 GHz', '26 GHz', '1800 MHz'])[1 + (g % 3)],
       100 + (g % 10) * 100,
       CASE WHEN g % 17 = 0 THEN 'PLANLI' ELSE 'AKTIF' END,
       p.lon + ((g % 100) - 50) * 0.0012,
       p.lat + (((g * 7) % 100) - 50) * 0.0009
FROM generate_series(1, 118427) AS g
JOIN seed_points p ON p.pid = (g % 20) + 1;

-- ---------------------------------------------------------------------------
-- Internal fiber route inventory (unpublished, 742,318 records)
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE seed_routes AS
SELECT * FROM (VALUES
    (1,  'İSTANBUL',  'KADIKÖY'),
    (2,  'İSTANBUL',  'MALTEPE'),
    (3,  'İSTANBUL',  'ÜMRANİYE'),
    (4,  'İSTANBUL',  'PENDİK'),
    (5,  'İSTANBUL',  'BEYLİKDÜZÜ'),
    (6,  'ANKARA',    'ÇANKAYA'),
    (7,  'ANKARA',    'ETİMESGUT'),
    (8,  'ANKARA',    'PURSAKLAR'),
    (9,  'İZMİR',     'BORNOVA'),
    (10, 'İZMİR',     'BUCA'),
    (11, 'İZMİR',     'ÇİĞLİ'),
    (12, 'BURSA',     'NİLÜFER'),
    (13, 'BURSA',     'OSMANGAZİ'),
    (14, 'ANTALYA',   'KEPEZ'),
    (15, 'ADANA',     'ÇUKUROVA'),
    (16, 'KONYA',     'SELÇUKLU'),
    (17, 'KOCAELİ',   'İZMİT'),
    (18, 'GAZİANTEP', 'ŞAHİNBEY'),
    (19, 'KAYSERİ',   'MELİKGAZİ'),
    (20, 'SAMSUN',    'İLKADIM')
) AS v(pid, il, ilce);

INSERT INTO cbs.guzergah (objectid, id, adi, notlar)
SELECT g,
       CASE WHEN g = 742318
            THEN '742000000'
            ELSE '74231' || lpad((100000 + (g % 899999))::text, 6, '0')
       END,
       r.il || '-' || r.ilce || ' F/O GÜZERGAHI',
       NULL
FROM generate_series(1, 742318) AS g
JOIN seed_routes r ON r.pid = (g % 20) + 1;

-- ---------------------------------------------------------------------------
-- Staging table (FTTH_ENVANTER batch notes) and the special route record.
-- ---------------------------------------------------------------------------
INSERT INTO cbs.a90312 (aciklama, durum) VALUES
    ('FLAG{unpubl1sh3d_st4g1ng_t4bl3}', 'TAMAMLANDI'),
    ('FTTH_ENVANTER_20260814_a91f3c.zip',     'HAZIR');

UPDATE cbs.guzergah
SET adi    = 'İSTANBUL-KADIKÖY ANA GÜZERGAH (TEST KAYDI)',
    notlar = 'FLAG{r0ut3_n0t3_0r4cl3_r34d}'
WHERE objectid = 742318;
