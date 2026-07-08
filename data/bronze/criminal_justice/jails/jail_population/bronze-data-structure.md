# jail_population — Bronze Data Structure

## Overview

- Topic: jail_population
- Source: jails (Georgia Sheriffs' Association monthly county jail report)
- Files: 223 files — 222 monthly HTML report pages spanning 2007-11 → 2026-06 (missing months: 2008-01, 2008-02 — empty in the source archive, intentionally not saved) + 1 convenience CSV (`annual_totals_2026-07-02.csv`)
- Unreadable files: none
- Year representation: filename pattern `jail_report_{YYYY-MM}.html`; the in-page report month (summary-table column header + heading) matches the filename month in all 222 files. Calendar months, not school years.
- Filename-to-data year offset: none — filename month = report month (verified programmatically for every file)
- Detail levels: county (159 rows, one per Georgia county) + statewide (summary table and a county-table TOTALS row)
- Percentage scale: 0–100 with `%` suffix — but corrupted (×100) in 38 months and inconsistently rounded elsewhere; all percent columns should be dropped and recomputed (see ETL Considerations)
- Checksums generated: 2026-07-02

## Source Provenance

- **Source URL**: <https://georgiasheriffs.org/jail-report/> (current month) + on-page POST archive form (`report_year`/`report_month`, 2007–present) for historical months
- **Retrieved**: 2026-07-02 (UTC)
- **Method**: scripted fetch — `uv run python -m src.etl.criminal_justice.jails.jail_population.download` (plain HTTPS GET/POST via `requests`; server-rendered HTML, no JS needed). `--backfill` sweeps the archive; months with no county data (e.g. all of 2007 before November) are logged and not saved. Full details in `_provenance.md` alongside this file.
- **License**: no explicit license posted; openly published factual data from a nonprofit association of public officials. Attribute the Georgia Sheriffs' Association. (See `_provenance.md`.)

## File Checksums

Generated: 2026-07-02

| File | SHA-256 |
|------|---------|
| annual_totals_2026-07-02.csv | 1906668a71069a28682cd0326f3c218d348d6a7120fa228c87a6668355e01373 |
| jail_report_2007-11.html | f7f99ee6856648848a82a73def068fa9c8f5a762ea6dcd0753769ff8c3a196cf |
| jail_report_2007-12.html | e2be7b2db254624a229bf74f7b7674ef085b2c2950bf18466546e078edb236bf |
| jail_report_2008-03.html | cb5d99eb1a0013213fc2e18a124676d90599dd971f9b3b39c76f210b9d206aa9 |
| jail_report_2008-04.html | fe02d980c03502a806d574bdb5b7e8a59d0cb6da12bc24c7d4a1faf4afddd3ad |
| jail_report_2008-05.html | 55decdfaf9a77eef121561ce1dbdcd027090bb71097b7f89381cf13f778c7cf6 |
| jail_report_2008-06.html | 310b6668c3546bd9a47f0ad88b6db4063a66aba0414a9f620c7d5ce54aefabb2 |
| jail_report_2008-07.html | c21debd9680ee283bbb48d41b39d1e15cf7ac20ed07968e291c2892515a9ee71 |
| jail_report_2008-08.html | ce0f54c7c6e91de50cf0f43139a98ddd3b59a679ec9931005af1e3291b2142fb |
| jail_report_2008-09.html | 26f956ae6372194fdb312c4a925826ce2ad24bf7b85dcd1db590ddaf92d38c7e |
| jail_report_2008-10.html | c1d6211c3d47b3d8ea57597bd5c6ca9325d7ec2417352cf3779fe073cbe46ac6 |
| jail_report_2008-11.html | 3fdbc8b3cdef250b2a360bc968ffd812958cd19bedd40b5a9664e2688d649576 |
| jail_report_2008-12.html | 1579b28b58ec221e48dc81096fd2be0ab25e2cc1f9ff569dc1f9aba9484a4ea2 |
| jail_report_2009-01.html | 3a37e8f3ad33ff116f2f0a9e5fc678a68fb92ede4d56d1493e2b0b705955b9fe |
| jail_report_2009-02.html | de85b38334dd28c7498be0a1a9ad00c4172ff77e87ab985a4c0c63e705af2f67 |
| jail_report_2009-03.html | 3e6bdc729f9b32a2e225279e7448b8c1e95ab74da8f47ef4af31466c933a75ca |
| jail_report_2009-04.html | 14cb41b81e00da94ae84cad163112085b202e24da73715ea15e995e6b09b6c41 |
| jail_report_2009-05.html | edea132906bec902e0a52542bcf1b3ab0f940651c956ae10cf6aa36ef30ac52a |
| jail_report_2009-06.html | 931555913e12409b4eef8e6d0bd9d65800dc2654d82cacfcae3a7fbe742ff106 |
| jail_report_2009-07.html | afbfc1bb876cdb6fe229f04937d0491e7b75bec3926e7b48b2a5c1519d3dfb08 |
| jail_report_2009-08.html | aa7750207f1df1a9ed9e8c8b7373ef0014b24c336878bc9653158c2723278a6f |
| jail_report_2009-09.html | ffe19481aa421c602b5e2962eca0728b51862cd4aa30b0f8ff3d0c2a19eaf66d |
| jail_report_2009-10.html | 7285bc0cc86e346f274bf60d67034b3a63dc4b58f557998060910c4d8091c201 |
| jail_report_2009-11.html | 788cae270946fcaeb366621ae0d97df856288521937a1c3ef672d4901159e986 |
| jail_report_2009-12.html | d4bbf4a977b1eebab69b0eb650d06d09c3bc941b433b9efe6a47044b9758b6df |
| jail_report_2010-01.html | 41d603b9297007be9b7a5926b273dfe2f4f72cb3d61874f315057a650bf0ed8b |
| jail_report_2010-02.html | 4698bf3233593c99f4db35f6257f20fd29615049252581c639e2778a5e1bc42d |
| jail_report_2010-03.html | 76e4ff9ea4b46a110bb0a4bfd9d8a51e32dcfcf7e8a956e91544a82f6d2e1cfd |
| jail_report_2010-04.html | 5d484953f8c351a9b7c366e9cecd0ba0318c2a3dabf02f4eba27ad461bad2838 |
| jail_report_2010-05.html | 8a7123dc1604005b613be89be9a787340edbdcddde6620b762f14b79ca3d339a |
| jail_report_2010-06.html | 7c5191a98929305be63ff08fcc092e229431929f9bb1085c195fe932b707718f |
| jail_report_2010-07.html | 3412286a3533ccf3191be55eaf6035b753a3df6eab2d3ff3615c136abb3c62b3 |
| jail_report_2010-08.html | 77f83dc863dc719b27dee544e24f21ceeeef6fa703a9777950e90442d476bf01 |
| jail_report_2010-09.html | cfdc63f11e49647d7929cef8843efbe0aebd252d62b7cddb8e22cda7dd74139b |
| jail_report_2010-10.html | 511a9afd5abea293c8db41b75a1fe3b1a68976186f1829fd6de64c0896d04551 |
| jail_report_2010-11.html | c2c7217967bfd79423907cac8a6338159080c1fba6cd2168304c8479179af6cb |
| jail_report_2010-12.html | 5b102939c6f3048a49667ce5c2f5d03cbc00375c44ac1dbc5abb232534efe975 |
| jail_report_2011-01.html | 6e340daa4d215383f0bc7c900dc75c80c4d2d2154f75b6a421b4540a813e8126 |
| jail_report_2011-02.html | c8a07c9c31db5fd49f1679db7cfb897a9e5d63f31c1793cbc4edc656ef3e3519 |
| jail_report_2011-03.html | c982ba7490cd21566527d39fdd6c1e646db8de48af7902aa44a2e1f21ed1ccda |
| jail_report_2011-04.html | 0f429cb47107c596fa9e827a7ae52c160ff906730c195c04f742c210cdd2bc30 |
| jail_report_2011-05.html | 5ac8e9220fbcc4d637199ccc92eb3dc1da9a24a31271fd5813f101ba37a391f4 |
| jail_report_2011-06.html | f88b08994340567851ca77f2f9c8f0d97f472858ab5091c80798a24739866ab5 |
| jail_report_2011-07.html | 19a918db617d13c5ecd4ed94b739f182b6550f86602445bc8ea772243c841ef2 |
| jail_report_2011-08.html | 05cf241023296b86caf6cb09a6816406e5242e10dfdd614224074892e9b001bb |
| jail_report_2011-09.html | daa9f188f6205cf59975c2041a9e16f4d2449cb018b0c1e6100eb52a8188c63d |
| jail_report_2011-10.html | 27167e0b84d93674e711391e4aac2a4fad3e378bd8356213281e7b30eecc22f8 |
| jail_report_2011-11.html | f01f8401efe6686c5ddb3ad47b61ab03eac2ccf1e88dfac6c12473c67c170505 |
| jail_report_2011-12.html | 2299160d1bd14d032a1d3223874fd7069bb0304b4cd818241320ccccd2586e19 |
| jail_report_2012-01.html | 99db5d982e1f4403f91ab31347291619b1876afa4ac720a12aac9ca5ab316001 |
| jail_report_2012-02.html | 87a4140353c2e1da2124afc81d971d3066ae6126f00088091849f82cb2e844f2 |
| jail_report_2012-03.html | 575d45d2957d907c8774d415eca1389cd5426cafe2e5d59e4309fa7a31115eab |
| jail_report_2012-04.html | 1512ae31dfa4d65c0b4b8ebd7abba64b60d3621a597ec708d95021ee99c6e58b |
| jail_report_2012-05.html | 16e004fa769e7137ee81e51329c14200802cb3ae83dc465013a54b4ed8252618 |
| jail_report_2012-06.html | 01876b1020baf740c0e9c9336cc4f9b12b8e4aa86764725b50054a1a91f2aabe |
| jail_report_2012-07.html | d977f66250ee29a0d871b385699810295fb04647393ba2ce67335e75844ac923 |
| jail_report_2012-08.html | e7205fefb524e9bf83857a10f7d3922db65b64353c23e5335533d212a72885b9 |
| jail_report_2012-09.html | 99fb0dbe21faa179a4dc39a6900d349aa7a49314cc38e136cccf236531abd2e7 |
| jail_report_2012-10.html | bd625c05170001825146ec9399cb140b7810f6ba2a05b9cf79069a8a491e0292 |
| jail_report_2012-11.html | ee3605b3a4da573025c07da88ca1d178e7caa90918cb6f82c7309a607e39ba66 |
| jail_report_2012-12.html | 61517aba3034009a75c22b9c1d5ea7b982f87725dcb8d7b40425fc0401c2994b |
| jail_report_2013-01.html | 6aa35618426f62c8a142a7b094e9a297fa1d3560e3b026df989e9f28f8c5dcfa |
| jail_report_2013-02.html | 985b81a4b8dddd5bef2975cceaedca9d40719c842fdd7f2aa0402867c0bf166b |
| jail_report_2013-03.html | b122a878f69c49c4f4275319e94c0ed8b548b76779c22d4d72154986ca8e088d |
| jail_report_2013-04.html | 993b73e74c43d781ae11556444789cfe2a8b144ab8941f37af47a6d31c7686ef |
| jail_report_2013-05.html | ac2df06858371d25a9a2cc95a6717b192f48d4fb0f8acad716ea9d204a27c880 |
| jail_report_2013-06.html | 86dcdb892583e80bcdee64df6c086e1fc06c6d756369120fdaa6bf953664f8cf |
| jail_report_2013-07.html | ac3f6b65d80543b242ff8bcf8996afb05bd07e91395921ab6c8287539eee6bbe |
| jail_report_2013-08.html | 44daefb36e371ad4cc6cc4ab9690d62af09683ca659fbdc8baee7384a45d6b89 |
| jail_report_2013-09.html | db466634083a66dec06c7388466d1867c34ea268fe1407bafcbe94722d6467e6 |
| jail_report_2013-10.html | d16ea5e49427239b53afcf0746bdb682787e80f602a2d70543570a28cb78d6cc |
| jail_report_2013-11.html | 6dc610aa44b6750755836bac53fdce460dc355068f673e11e8d865d3d0e9cba4 |
| jail_report_2013-12.html | b8898c9503035d380e79f781a3715e647861df576d4c7abfa4634d6a6f290b5d |
| jail_report_2014-01.html | 52b5fc5d6296488792e883ecc012e4369dc69d991967ded52f6b1fd4819255bc |
| jail_report_2014-02.html | e6860467d2710c4532d19c374a8516fd510de24993f634db6282677bfb7ba811 |
| jail_report_2014-03.html | a013d5445d263575e16a38e10055a67cfd770a18cbc10f1085895fd4ed06e271 |
| jail_report_2014-04.html | 4d66f508682266912ae9a70f088af3a6cce302c9d51588575423e6bfa1ce8d6d |
| jail_report_2014-05.html | a6c9275468c8d357caa80769e2d38ef433a355c1ebbaf6509d228f0f14e1064e |
| jail_report_2014-06.html | 64ff1a03402f7a2173eb6be8eadcf043b04d3e0122c79ca2ee2468eafd9452a1 |
| jail_report_2014-07.html | c20e5d4e13e9bd5bf82a08beee5599062c3e5ae00f26a754c41f951c5704703b |
| jail_report_2014-08.html | 1632ade943d56a749e849eb9b7b011fa8b8b85bebf36720d78b6d2d7c97b0730 |
| jail_report_2014-09.html | 9875ec395d6611b7a60c7858f73b729cc7aa4b4850194c19af054bda07edc8c1 |
| jail_report_2014-10.html | a82b3530ce9bae3846902acda7960b5e281e0b22a4f5773908778dc514b0f47f |
| jail_report_2014-11.html | 1643c11c808bf39aab23e94ba3f5b761baea287b120a1bd2f233f77be3215bb9 |
| jail_report_2014-12.html | 51e3701e669ab56d4a2b5f921c2f424b3bd98b0bda05e92395d490a58f09b6d0 |
| jail_report_2015-01.html | da5f7685e5e84cdb0d266c428ddcd3a96d970ec750e28f52122b53a13c86222d |
| jail_report_2015-02.html | 767ee254bb0222a79d7fea6b5ce845451c35634f9bad47bfc33b1fff6131a49d |
| jail_report_2015-03.html | 335ea97cbaf5ba0266d611ac0cf1362151d065a31c8bfab8bfdc5f87c30e0f41 |
| jail_report_2015-04.html | 80e1b9fdd2cad92a80aae90e13163b70ce09c2c8a434df6b7efd77d4019b4be0 |
| jail_report_2015-05.html | 5d6b81d43a19459d88c7f279d7f537900907b9f417b1c1b9f2d6e9c9eecbe9a7 |
| jail_report_2015-06.html | 327a5358e3ec1ae308da232abd82026826ec175cf50c46a0224197601412af4b |
| jail_report_2015-07.html | 75cf196a86904ac57d3dbf79e7927e5eb363acc12e5d5d9e22e7ace9ea5533ee |
| jail_report_2015-08.html | a8e2cf58ff3f1c8be2b37973750478546a0dfd29d678c2e78cb1eccd469da263 |
| jail_report_2015-09.html | 471ded325b2be6d8b1e78553ae4dfa0ae7442615215a26e8370e862c2da79edf |
| jail_report_2015-10.html | 04107c40e4c9df524820dc90256126a8b39e351e642e06f5c364e8954a86f48c |
| jail_report_2015-11.html | 84451dde200a08f8a7e9163c3454d5aca29448db24fd80324c6143c135678af1 |
| jail_report_2015-12.html | 4158bcc44ed8552fe6b1f86e7518bc4fb6adce872b5e5c4139affcb7f2afbec4 |
| jail_report_2016-01.html | 45128150096ef36889e35a63efe28ff265cd464c7609725482797d58cc09058a |
| jail_report_2016-02.html | e9cca8e617626e064f536ef3c866fe1c47274e99b01b7512885752ab8d6d970d |
| jail_report_2016-03.html | 2e2852fa95c0dfb4cb7116afa3e15c6fefb21c13f7896a945462ba677da51f11 |
| jail_report_2016-04.html | 2c0c9273cdcbedf507ef8a93f99c837cc39a4bdeb487559a6600e8f6e172749e |
| jail_report_2016-05.html | d1d2478a7632a658b56fdc8d6c5d80dd70843f08b2f8f690ee876764247217c5 |
| jail_report_2016-06.html | 9704c308f4ce2f369e1edd51c134dc60ee2326ccad94f1284d0b4155b70602b2 |
| jail_report_2016-07.html | 35c7c2682c956b96405edc8178fc358a1067d643e85854622aca35c08ce09874 |
| jail_report_2016-08.html | 6e2380f957e16ee9339e7d16aa8a485937178c3eeffc74ef6e16bc7fda750684 |
| jail_report_2016-09.html | f51f09f58e914b8ed38f4b717503d23d1ae296243f0f801d5863654ef13567a2 |
| jail_report_2016-10.html | 70e359579a73b26c95ceb2db39a946f54ec6ed30ab9bd5efeade0fe50c6af43e |
| jail_report_2016-11.html | 173cb21a352089198c385f203bdfe3e68e32fe3bde59b72260bc55a52d1a7f87 |
| jail_report_2016-12.html | 74d3d1bdd51da9b540d0c76d4681d75abdf97556dc11ffbe99bbb92ed06a95bd |
| jail_report_2017-01.html | 12e365b1c0358c11d4da4ba201e9bc0521acd63fd1a357562b90161d97f18d6b |
| jail_report_2017-02.html | d1c3f76fe71fd5c100ca815ad4454fefbeaee984b87c946b8ff5cf41a7f7f7eb |
| jail_report_2017-03.html | 008b61a40cc76c761a5e8911ecaa32198f2e13b6da8472759867d26bce7be55b |
| jail_report_2017-04.html | c7c6f3c163331ec6824a40579d68ec941640767e75aae71f5c70ddd47e27cf7e |
| jail_report_2017-05.html | 99c80f96d5ad3a317828dde3d6bbdf804b9531d73c8022772ec1a67ada0608a1 |
| jail_report_2017-06.html | 2a2e780674309a2276fcab21aaadef1209c9ec50f45472927e44e7da1ccfbbf1 |
| jail_report_2017-07.html | 88cc85f844b1b9801d6e467f82ca6af0f0b139a9616ef56ef5214fdbfe18ce52 |
| jail_report_2017-08.html | 6c32352b15a3091827895da76554b9c04c62bfd4f8877ecbd18fe3eddca8c00c |
| jail_report_2017-09.html | b782d74fb59c0b12b7500a00e01e2b636d88f106e5c85e80abab625a03134339 |
| jail_report_2017-10.html | 8dfeb01901ae42c306575fc358d4a9a396805e29e4aa3b6f5bddae6465d16508 |
| jail_report_2017-11.html | 2ce414fd6732081db9fdbf0a31b94caa3025be01066151006c3f1023de5e1445 |
| jail_report_2017-12.html | 29991343c6b7f38bc9a711b78c5337d0bd434fcb9a8d7b0a44e5885bb8b1916f |
| jail_report_2018-01.html | 7dd9e98907c030525c6cae9ab777623b34448a1e736f2c3844644fc71c24e8cc |
| jail_report_2018-02.html | a826ef0e32e078e2f2b9158a7e5b93c9eff9ea297766e0e3fcc93c5e6c73b10b |
| jail_report_2018-03.html | 8be21e777346009fdd898f65fe649a931a99982038c02fe97f217346bdbb6453 |
| jail_report_2018-04.html | adbd7d7c13f139a743adb3b8e3f9f2e60b2ea4567e49569223393b238d347620 |
| jail_report_2018-05.html | 0e4a0bb0e520e3bf9b0d0f8c798b71a5612515e00c6bc2bb18dd15b5d4b58c98 |
| jail_report_2018-06.html | c1243c5e632408ae360ee0a5122af77492dfaae554322b1bbc94127f698afcbb |
| jail_report_2018-07.html | 7f5f696319d23a3064977de4a77c5d743adefeb3f28eb0d49188951c28405d8a |
| jail_report_2018-08.html | 6898168e5fd53b4be684f7007becc36e941a822094d4d41654185d939beefd0b |
| jail_report_2018-09.html | 66105d518fb70bcc0674dbd8d83c5319b8195601609b31e4242aedc9d985b6b0 |
| jail_report_2018-10.html | e8b729f50b01123689147249465c71a3649727ef110057d2143dd6e893cf5b01 |
| jail_report_2018-11.html | d9bacd0069066b8f113ebe099f413c489dc04c9108c67f5e29b65c4109c82f2e |
| jail_report_2018-12.html | 6089fc1681ceb0d7053e1dd767466dff0a0beda1831495c183b21bc5822f6d0d |
| jail_report_2019-01.html | b393e797f5d2d0f212d3a74677a3bc581ae0edb80ccdfc491b1f1e582cca5553 |
| jail_report_2019-02.html | 42e8ac5f8dd9b21f34dac680363cfbc12102daf8541533c36244ef1c450415d3 |
| jail_report_2019-03.html | 587260c705ebb045c87eda6566b3ddde07ece36aee58634da3d03f1bb67afb69 |
| jail_report_2019-04.html | 0d0afef22b6e5e83d9eafe2f0a034107999c28c03c09c087689344ff80aa27f4 |
| jail_report_2019-05.html | 2ef802f0e803b63ad2a01c61a3748662bbbcc81cb8d6271388390a461e71491c |
| jail_report_2019-06.html | 57a5b48d9f0d1b73a9eb70e03a702d855129f29e14c769f3b13864c4629e6484 |
| jail_report_2019-07.html | 0582440e31cdfc49bdcd8bb999553dceee0dea20bd77db7730e7786c660d31c0 |
| jail_report_2019-08.html | 7fa3469f969960594554e3b57a29016f31e8402aaaa7942f25ca55895fdbd117 |
| jail_report_2019-09.html | 5378f981f48cb3f0d3f3f8a8a35cabc083e4f791170315daece21cd06042495a |
| jail_report_2019-10.html | 74ba569869ae568fc68894076f23b89f1b3dec8855a7beff23c6cabec1ab986f |
| jail_report_2019-11.html | 196ed1ea73cd80aac6327059c23eff6d4158e4aa6ffaef97ae928fe969c39c82 |
| jail_report_2019-12.html | d5f8049b2b9ec202daca776568626550b30f9c32787b86b2564b9811d0c687dc |
| jail_report_2020-01.html | 79167d102aed2dbac1ec2267dbd6235edd6dccc017cbf8e9772d08422f399e84 |
| jail_report_2020-02.html | 2a9d75e6ddd267edc2ea40134015fd5295eac48ae9371d45595f54f847aa3d7e |
| jail_report_2020-03.html | 7b7c4dae7d4bdf349e38e06fc112104fed69b2d3713dffefaed7a3d47cd29691 |
| jail_report_2020-04.html | 649d9de00eba2d72e0c2dc1d5b496fe427fa34558a03adb160819fc2d9a3d723 |
| jail_report_2020-05.html | 0417a603ed729e5b83457fbc65f7e943e360790a0b0be6715b40350f4ed49412 |
| jail_report_2020-06.html | 92b6cc833ea84c35fea559eeceecd6b6ffa6aee6b7f3ed1445d261dbd6adbc2e |
| jail_report_2020-07.html | a2182fa7f81aa548d1731fc9e6bd286980eb63b969ec128e5645bc0983d00c75 |
| jail_report_2020-08.html | e663a6adbaf401c3bb93c2567b87f6952f62c82bb6d43a66fd8f0ebc031fd210 |
| jail_report_2020-09.html | 9491d344c4b4597b8b4281bd21b1156e60bfce22169b413f2d0ad7a4a7335aee |
| jail_report_2020-10.html | 1e17621bee5eca13bbda6003978a8384f8d9a755925f0cfa263939cab40fd90f |
| jail_report_2020-11.html | f03afefc64e357e7c09cf30524cb1ed223c3b35097507230a673a7436974ef03 |
| jail_report_2020-12.html | 38052271e67ba5fdf7e1b50fc29914473b542b530989620ef153978381ab84ad |
| jail_report_2021-01.html | 92743cc20d639cab41851f4bac10ef8d987078644057a0f4ad0435797ad77e59 |
| jail_report_2021-02.html | 26ae3b4d59f23ecc98ea3456ee560d246034f688cc1327f45e0fe877b0e2846e |
| jail_report_2021-03.html | da9e38c942034a42b01e1f8711084eeb4d4e55706dcbae35d0a272ae3b47eb34 |
| jail_report_2021-04.html | 93aca037627537e4c23bb27144741842e575804d2529cab6e10278b63bc36bf6 |
| jail_report_2021-05.html | de581c2e9b438fd80a3b16c672420518332343b0ba64c541f5117404886a9a63 |
| jail_report_2021-06.html | 3b7647026267ad69960ce7b7c837df8e88ce9fcc26e9a2971b0f80f4fb6a924f |
| jail_report_2021-07.html | 119c77978acc409f42a334051d7ebabdb2613b9002b73b27ddfcac54897b2fad |
| jail_report_2021-08.html | b564917c629a8b6d66913f739e210a1f6ad4a0842f692a4cda38ead6ceea51ff |
| jail_report_2021-09.html | 26f96c92935799ec21e49eace51aaea3d336d318e45955a759bad0348faba2ec |
| jail_report_2021-10.html | 4e7b170de8cfdca109236b35924286cf4c75a0d2a2274a7db3ef66595ebb31f0 |
| jail_report_2021-11.html | 5626002bd42d4d7965c4f07e45d0ee3514d7a3d77609e8d6e7dddc6bace8d9ca |
| jail_report_2021-12.html | 8ace478c129a83b90f2eadc4c4061775aa800b38f9869846e3c648649f611d2b |
| jail_report_2022-01.html | f5300f244f75b190f39610340aa03131543446b7321d4040c422d6aeefbbbe46 |
| jail_report_2022-02.html | 01d11079c9a5652e8ff6b25ed4e2f08aab44dd734e2563b31c8a101cbdebb404 |
| jail_report_2022-03.html | a64c5e30cdb91eb4a67c154b5d6855f0d086d411c7887cc7f54821ee1d39d118 |
| jail_report_2022-04.html | a20ba4616185c5490a513ff7adaceeb34a3d9f98b00361939ec04d27b6d19170 |
| jail_report_2022-05.html | fa3ecac4251e679def8d14d963cd11980787dfd6963fb1104e23e08b36f5e0f3 |
| jail_report_2022-06.html | 718c10bb6f4dfc276b9ca01593b4540219cac2ff4b47284d9c41f68765a1713f |
| jail_report_2022-07.html | aba884c69ae1650951f87e5dbddc772addcf5e20a113df1eab56d382c916ac8f |
| jail_report_2022-08.html | b06d7322cefb79338e89807425dd62ca1d5df6591bcb1672fa3c5fd6519114f0 |
| jail_report_2022-09.html | 105178d82c5a3e714ce30a234975f6ab8d00b533d24cccf82c3182554033721b |
| jail_report_2022-10.html | ca6c60d9826bcf719d8453f3cb0823c195ba7d688902511f553e02311351f767 |
| jail_report_2022-11.html | 7849253a514a0f2c4cb4df3e94c4b4147b5c6d86938154111cbdc00d56702a8d |
| jail_report_2022-12.html | 479e609eba7dd8dbe4bce832e284bb74866bb4a20703dcffada595e88fe62a9b |
| jail_report_2023-01.html | 7c9aeade4280510eba88a439363d6af7cfa6855f0939d4ba438ecdff180ecae6 |
| jail_report_2023-02.html | 3afd7338cbe9fe11c063a8d695e52418bdd8c6a2aaa689918320b0edbc1e5e52 |
| jail_report_2023-03.html | 46a70fd6385cf991e8f406683984ab5a43f6e7ada1b984edc66636b36a59ac5b |
| jail_report_2023-04.html | 120dc99c4a4407d67efe20a08c0ecf425fc1af136f1b41f009ea830c4b46a5f7 |
| jail_report_2023-05.html | 47947cf7cc296b1c4230178782fb26b525ec63a9110a713a4757ab7f0b30b5ab |
| jail_report_2023-06.html | 08cee175a4afc4f6b37ad4fc464351c999fd082acaa8aaca548f36a53cb1c44a |
| jail_report_2023-07.html | 4f4488d8e8a66f0bb1ee52507cfe45b7549684d3af3199327a7c7e5543af1af3 |
| jail_report_2023-08.html | 000a29f1b7cb8ed40f572d56900868bea48f2e39ce45adfd38c295d430e52bd0 |
| jail_report_2023-09.html | da5f18b9c59fe8668998fd9a1278ba9f673dad826bf40273dea91a4cc59aab86 |
| jail_report_2023-10.html | eca595bab3d04d5f409f2cd27ab62a04e94919e70ee108ce6708bfd2c36d6dd3 |
| jail_report_2023-11.html | 72f53134b04d32a2b39b2ed941797faac1dcc46a08f1ae411dbc156daee61ef9 |
| jail_report_2023-12.html | 83d58264e09ad342fd4e32a975985dcb0e786c6c3fcfaa674d50d41819312cce |
| jail_report_2024-01.html | ef9cfc90a69b6a7508f5d3ba5b3d79c00249648b00ecf29b1c3cdeccb5eb32bf |
| jail_report_2024-02.html | 3ddc02cd511d5ca297baaedcc741302e65cdb6f91266529f3b87ed2741c9c138 |
| jail_report_2024-03.html | 6f4817478f15fca5254eeb1e6ecb27d83bae02e758177d00e2b7905b10c0b7de |
| jail_report_2024-04.html | 119f80254bbee19ebaf6dad3de030864dcd71400cf6f65a3d4ef991c7949b6c1 |
| jail_report_2024-05.html | 4b666d82260c140c3bd52b410589f8036b410ec27929019af9b17f62aaf9adaa |
| jail_report_2024-06.html | 69d9d0c79dac4dbd2792755cae145061480ddbfef420c3153f2d5f9b9988c4ef |
| jail_report_2024-07.html | ceeb734dfe6ff19927609daf48850af4a93bcda2e8872f7b8c6e98d5fce0f929 |
| jail_report_2024-08.html | 3913b9a518ff77ec841a83e0d1d52392dc7430b7c1b5a1703e47254abcdb4f81 |
| jail_report_2024-09.html | 0e270e20550a4479f0039068cd68abeac4de6b6065f825309dfc6774319e86ae |
| jail_report_2024-10.html | 8040fa6b16bd0551fd03ecee933ae2f5b5d892e55e860b41a0ada44f571555a6 |
| jail_report_2024-11.html | 1b1b38140c3ff3b7553443a28c403da89848360f7f8d9ed3a7a3dc6c7608b554 |
| jail_report_2024-12.html | 8c41682e24dcd5b9c0c0147a33a0e5a2628a3331b5ec27ffaee5b44f4d111621 |
| jail_report_2025-01.html | c5f3c0a78775ea0ab17337bc9fe61f1d9b9d4c6364c2d88f4aedc3d1f382aa95 |
| jail_report_2025-02.html | 7379be13481571779ad0204d18dbed2b508e9a93a1f7706d20524fa533de1393 |
| jail_report_2025-03.html | 27a69e87e0da0c5b5055de26e77589753ee3b54aa2c990619cd56896e29ea77e |
| jail_report_2025-04.html | 3df6726e52d6d2e02aa8615fa6ea47705559a647dacfabcdf476f27b041b595e |
| jail_report_2025-05.html | d2f0a015392d16cd88f25e4a2670541328ba0858940300f3519ef5c59f998911 |
| jail_report_2025-06.html | 0578bab4c33c3d35de79d4b7d4f7cdbb66f53f168bf62ae387575a173cad34fe |
| jail_report_2025-07.html | b1d5f25285adac2e85cfc6d46dbc48360bde3797a6b9ba5005c7bfe2f611c08c |
| jail_report_2025-08.html | 6ba94cc774a5a3e06af38431806c6cbcc1d5238c189c70a5573e14a6e5fc04dc |
| jail_report_2025-09.html | 691a8952176e153f083f2771a5e7086b34e24b74e39314b529f84acc139c14ad |
| jail_report_2025-10.html | 91c57878d3c487ca2ae0b30fafbc117cb89f431b183087dc9dede8bc9325e146 |
| jail_report_2025-11.html | 1c898950640987e8658f7b260ce7e2d18b03e60e866749afd760aa44517a7b34 |
| jail_report_2025-12.html | 41cc52c84b95f6a0a0a6a4c19ec29d7398c70cf07adc38a03e8f78a964bf2385 |
| jail_report_2026-01.html | 68708244abebd9d4e6e5ba5ed2855584a22df2ae6a15a2140bd4a3bceb4bc579 |
| jail_report_2026-02.html | 24dd4d3c8093744c6cabcb0df4c9eb45fa8922b8bfa382fea7480e0b5899fa20 |
| jail_report_2026-03.html | 257d6b4dd6d00651e7e4a35eb929aea938c192c10b741e9f6504f087b5ca6baa |
| jail_report_2026-04.html | 59c3649c4c14bb55aa923962617043322a8c6ef1e166099ad88ebb6471f48f67 |
| jail_report_2026-05.html | be137bafb7daf6068c1928084e3b3e1a989808a19542cd478ad3ec8d0e4f8bab |
| jail_report_2026-06.html | e630b03992ed8f854f471ae9889437e21c1e4334316b912bfed0910c9244aece |

## HTML Document Structure

Not Excel — each bronze file is a full server-rendered HTML page. Structure is identical in all 222 files:

| Element | Contents | Notes |
|---------|----------|-------|
| Table 0 — statewide summary | 14 `ITEM` rows × (report month, prior month, Increase/Decrease) | Month-specific. Reflects **reporting counties only**. |
| Table 1 — per-county table | header + 159 county rows + `TOTALS` row (161 `<tr>`) | The primary data. Header has 12 cells; data rows have 13 (leading unnamed row-number cell) — parsers must handle the offset. |
| Chart JS array 1 — category breakdown | `arrayToDataTable`: Awaiting Trial / State Sentenced / County Sentenced / Other | Month-specific; redundant with Table 0. |
| Chart JS array 2 — 12-month trend | months × (Capacity, Total Population, Awaiting Trial, County Sentenced, State Sentenced) | Month-specific (anchored at the report month); zeros where the archive has no earlier data. |
| Chart JS array 3 — annual totals | `year, total_inmates`, 2016–2025 | **Retrieval-date page chrome, identical in every file** — NOT specific to the report month. Do not parse per-file. `annual_totals_2026-07-02.csv` is a verbatim snapshot of this series. |

Statewide summary ITEM rows (constant across all files): 1 Number of Jail Inmates · 2 Capacity of Jails Reporting (permanent beds) · 3 Percent of Jail Capacity · 4 Number of Jails Over Capacity · 5 Inmates Sentenced to State Institutions · 6 Percent of State-Sentenced Inmates Housed at County Level · 7 Number of Inmates Awaiting Trial · 8 Percent of Inmates Awaiting Trial · 9 Number of Inmates Sentenced to County Jails · 10 Percent of Inmates Sentenced to County Jails · 11 Number of Other Inmates · 12 Percent of Other Inmates · 13 Number of Jails Reporting · 14 Number of Counties with Jails.

## Summary

Monthly county-jail population survey for all 159 Georgia counties, 2007-11 → 2026-06 (222 months). Per county per month: total inmates in jail, jail capacity (permanent beds), percent of capacity, and a four-way breakdown of the inmate population — awaiting trial, sentenced to state institutions but held in county jail, serving a county sentence, and other — each as a count and a percent. This is the only monthly-grain, county-level jail population series available for Georgia (BJS jail data is periodic and sampled). Voluntary self-reported survey: coverage varies by month (159 jails reporting in 2019-03 → 59 in 2026-06).

## Eras

### Era 1: 2007-11 → 2026-06 (single era — all 222 files)

Column names, table structure, and summary ITEM labels are byte-identical across the full archive. Columns below are the per-county table (Table 1); positions are the 13 data-row cells.

| Pos | Column | Description |
|-----|--------|-------------|
| 0 | *(unnamed)* | Row number 1–159 (alphabetical); blank on the TOTALS row |
| 1 | Jurisdiction | County name; counties without a jail carry a ` - NO JAIL` suffix; final row is `TOTALS` |
| 2 | Number of Inmates in Jail | Total inmates, thousands-comma formatted |
| 3 | Jail Capacity | Permanent beds |
| 4 | Inmates as % of Capacity | Percent, `%` suffix (unreliable — see ETL) |
| 5 | Number of Inmates Sentenced to State | State-sentenced inmates held in the county jail |
| 6 | % of Inmates Sentenced to State | Percent of total inmates |
| 7 | Number of Inmates Awaiting Trial in Jail | Pretrial detainees |
| 8 | % of Inmates Awaiting Trial in Jail | Percent of total inmates |
| 9 | Number of Inmates Serving County Sentence | County-sentenced inmates |
| 10 | % of Inmates Serving County Sentence | Percent of total inmates |
| 11 | Number of Other Inmates | Residual category |
| 12 | % of Other Inmates | Percent of total inmates |

#### Sample Data (2019-03, fully reported month)

```text
row_num  jurisdiction        inmates  capacity  pct_capacity  sentenced_state  pct_..._state  awaiting_trial  pct_awaiting  county_sentence  pct_county  other  pct_other
127      Stephens            135      192       70%           10               7%             109             81%           5                4%          11     8%
118      Quitman - NO JAIL   0        0         0             0                0              0               0             0                0           0      0
16       Bulloch             418      387       10800%        46               11%            260             62%           64               15%         48     11%
119      Rabun               104      102       10200%        0                0%             62              60%           25               24%         17     16%
30       Clay - NO JAIL      0        0         0             0                0              0               0             0                0           0      0
```

(Note Bulloch/Rabun: over-capacity percents rendered ×100 — 108.0% shown as `10800%`.)

#### Statistics (2019-03, 159 county rows, numeric-cast after comma/% strip)

```text
statistic   inmates  capacity  pct_capacity  sentenced_state  awaiting_trial  county_sentence  other
count       159      159       159           159              159             159              159
null_count  0        0         0             0                0               0                0
mean        234.9    307.0     1954.1*       15.1             151.0           33.7             35.1
std         415.1    517.7     4344.1*       30.1             300.9           86.9             106.9
min         0        0         0             0                0               0                0
25%         36       60        47            1                17              2                1
50%         88       125       71            4                49              8                5
75%         231      300       89            15               167             30               25
max         2624     3636      16600*        200              2042            820              987
```

\* `pct_capacity` statistics are meaningless — inflated by the ×100 rendering bug on over-capacity rows.

#### Null Counts

No literal nulls or empty cells in fully reported months (2019-03: zero empties in all columns). Non-reporting counties appear as **rows with all 11 value cells empty** — 74 of 222 files contain at least one such row: isolated singletons before 2019 (2008-11, 2008-12, 2009-06, 2010-12, 2011-01, 2011-02), then increasingly common from 2019-11 onward (2026-06: 100 of 159 rows blank).

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| Jurisdiction | 210 raw values = 159 counties ± ` - NO JAIL` suffix ± casing variants, plus `TOTALS`. Casing variants: `Mcduffie`(182)/`McDuffie`(40), `Mcintosh`(182)/`McIntosh`(40), `Dekalb`(185)/`DeKalb`(37). 47 counties carry the NO JAIL suffix in at least one month; a typical month has 13–16. |

No demographic columns exist (no race/ethnicity/sex/age buckets) — the Asian/Pacific Islander check is not applicable.

#### Suppression Markers

None. After stripping thousands commas and `%` suffixes, every non-empty cell in every file parses as a number (one non-integer: see ETL Considerations). Blank cells mean "county did not report", not suppression.

## ETL Considerations

1. **Non-reporting = blank row; NO JAIL = zero row.** A county that did not report has all 11 value cells empty → NULL metrics (do not zero-fill). A county with no jail is labeled `X - NO JAIL` with literal zeros. Consider a per-row status categorical (`reported` / `no_jail` / `not_reported`). Coverage collapses in recent months (2026-06: only 59 of 159 counties present).
2. **The NO JAIL suffix is unreliable month-to-month.** It legitimately toggles over the years (jails open/close: Stewart, Talbot, Clinch, Treutlen…), but from 2024-06 onward there are one-off erroneous flags on large counties — `Richmond - NO JAIL` (2024-06), `Fayette` (2024-07), `Burke` (2024-10), `Bryan` (2025-02), `Toombs` (2025-09), `Johnson` (2025-10), `Emanuel` (2025-11), `Pulaski` (2026-01), `Coffee`/`Terrell` (2026-02) — each a single zero-inmate month for a county that plainly has a jail. Do not build a static no-jail list from any single month, and treat isolated single-month NO JAIL flags (surrounded by reporting months) as non-reporting, not as a real jail closure.
3. **County-name normalization before FIPS mapping.** Strip the ` - NO JAIL` suffix, then normalize casing variants (`Mcduffie`→McDuffie, `Mcintosh`→McIntosh, `Dekalb`→DeKalb) before joining the county name→FIPS crosswalk.
4. **All six percent columns must be dropped and recomputed.** In 38 months (2018-01 → 2022-12) percents are rendered ×100 (e.g. `9500%` for 95%; in 2018-01 this hits ~140 of 159 rows across ALL percent columns). In other months over-100% values are ×100 while sub-100% values are correct integers; decimals appear inconsistently. The percents are pure derivations of the count columns — recompute as proportions (0–1) if needed at all.
5. **Additivity regime change at 2023-06.** Through 2023-05, `inmates = sentenced_state + awaiting_trial + county_sentence + other` holds for effectively all rows (~14 sporadic violations in 16 years, including a 2018-09 block where the Macon/Madison/Marion/McDuffie/McIntosh component values are misaligned by one row — a source-side Mac*/Mc* sort mismatch). From 2023-06 onward the identity fails for ~70% of reporting counties every month (median gap 13 inmates, p90 ≈ 103, max 5,262). Keep all five counts as reported; never derive one from the identity; do not add a validation check asserting the identity post-2023-05.
6. **Number formats.** Thousands commas (`2,624`), `%` suffixes, bare `0` (no `%`) in percent columns of zero rows. Exactly one non-integer count in the whole archive: Madison 2019-05, `Number of Inmates Sentenced to State` = `0.01` (treat as bad data → NULL or 0, log it).
7. **TOTALS row is derived and verified.** In checked months the TOTALS row exactly equals the column sums of the 159 county rows — exclude it from county-grain output (or use it only as a parse check). The **statewide summary table can disagree** with the county-table TOTALS (2026-06: summary says 12,750 inmates, county table sums to 12,664) — the county table is internally consistent; prefer it for any statewide aggregate.
8. **Statewide numbers reflect reporters only.** Month-over-month statewide totals conflate population change with coverage change. If a statewide series is published, carry the reporting-county count alongside it. Summary items reconcile as: item 13 ("Number of Jails Reporting") = counties that submitted (including NO JAIL counties); item 14 ("Number of Counties with Jails") = submitters minus NO JAIL rows.
9. **Missing months 2008-01 and 2008-02** — the source archive returns empty pages for them. (Their statewide — not county — values are partially recoverable from the prior-month column of the 2008-03 summary table, if ever needed.)
10. **Chart array 3 (annual totals) is retrieval-date chrome** identical in every archived file — never parse it per-file. The `annual_totals_*.csv` snapshot is redundant reference data; annual statewide totals are the sum of the 12 monthly statewide totals (verifiable from the county tables from 2016 onward).
11. **Header/data cell offset.** The county-table header row has 12 cells but data rows have 13 (leading unnamed row-number cell). Parse positionally, not by zipping the header.
12. **Monthly grain vs year-partitioned gold.** Gold fact tables are year-partitioned; this source is county × month. The transform will need a `month` column within year partitions (grain: county × year × month) or an explicit annual aggregation decision — flag for `/transform-topic`.

## Gold Schema Classification

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| *(row number)* | not_in_gold | — | Alphabetical index, no information |
| Jurisdiction (name part) | fact_key | county_fips | Normalize name (strip suffix, fix casing) → county FIPS via crosswalk; county name lives in the counties dimension |
| Jurisdiction (` - NO JAIL` suffix) | fact_categorical | jail_status (or similar) | Derive `reported` / `no_jail` / `not_reported`; guard against the one-off false NO JAIL flags (ETL #2) |
| Number of Inmates in Jail | fact_metric | total_inmates | count, ≥ 0; headline metric candidate (`key_metric`) |
| Jail Capacity | fact_metric | jail_capacity | count, ≥ 0 (permanent beds) |
| Inmates as % of Capacity | not_in_gold | — | Corrupted at source (ETL #4); recompute from total_inmates / jail_capacity if wanted |
| Number of Inmates Sentenced to State | fact_metric | state_sentenced_inmates | count; state-sentenced held in county jail |
| % of Inmates Sentenced to State | not_in_gold | — | Recompute (ETL #4) |
| Number of Inmates Awaiting Trial in Jail | fact_metric | awaiting_trial_inmates | count (pretrial) |
| % of Inmates Awaiting Trial in Jail | not_in_gold | — | Recompute (ETL #4) |
| Number of Inmates Serving County Sentence | fact_metric | county_sentenced_inmates | count |
| % of Inmates Serving County Sentence | not_in_gold | — | Recompute (ETL #4) |
| Number of Other Inmates | fact_metric | other_inmates | count; residual bucket; NOT guaranteed to close the identity post-2023-05 (ETL #5) |
| % of Other Inmates | not_in_gold | — | Recompute (ETL #4) |
| TOTALS row | not_in_gold | — | Derived (verified = column sums); parse-check only |
| Statewide summary table (items 1–12) | not_in_gold | — | Derivable from county rows; disagrees with county table in some months (ETL #7) |
| Statewide summary items 13–14 | not_in_gold | — | Derivable (count of non-blank / non-NO-JAIL rows) |
| Chart arrays 1–2 (category, 12-month trend) | not_in_gold | — | Redundant with tables |
| Chart array 3 / annual_totals CSV | not_in_gold | — | Retrieval-date chrome; annual totals derivable from monthly data 2016+ |
| *(filename YYYY-MM)* | fact_key | year, month | Report month; verified = in-page month for all files |
