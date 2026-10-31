-- cc290 rollback: fellir alla cc290-hluti. scraper.listing_sessions (cc85) og scraper.session_config eru ósnert.
-- Gögnin í auglysinga_atburdir eru endurhlaðanleg úr D:\listings_v2.pkl (scripts c2 --beita).
DROP VIEW IF EXISTS scraper.listing_sessions_v2;
DROP VIEW IF EXISTS scraper.v_auglysinga_atburdir;
DROP TABLE IF EXISTS scraper.auglysinga_atburdir;
