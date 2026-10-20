# MP2 Report — Faisal Syed

## 1. What decisions were mine
**Client**:
- The client I chose was my fraternity, Delta Tau Delta (Chi Chapter). I serve as the president of this fraternity at Kenyon. We currently have an extremely old and outdated website. One older alum runs it, and it has not been updated in years. Members cannot make changes or posts. Alumni are also not able to find news or contact info regarding the chapter. Fraternity officers change every semester, meaning there is a constant need to update and change the website

**Where I overrode the model**
Q1: I was suggested to have the pages be admin-only. Instead, I suggested that different chairs are assigned different pages (e.g. community service chair edits the community service page). I did not want the president to be the only one who can make changes. Otherwise, we could run into similar problems of the one person not doing their job.

Q5: Listing admin; I wanted name + title + term year. When people look back on the website, they should be able to see how long someone has left in their role, and in their time at Kenyon.

Q17: I was suggested to have no event dates; I changed it to having an optional date. Many posts will be for things that are scheduled, like a rush event for instance.

**What came from the work on WordPress**
The most important thing was in regards to the WordPress refusal page. If you were refused access, it did not state who the admin/contact was for the site. My site does.

## 2. Drift, and what caught it
**The weakened security test (T02)** 
In T02 a test checking that javascript links get blocked failed, and instead of fixing the code, Claude changed the test to something narrower so it would pass. My guide chat pointed it out and I asked Claude about it before pushing. It turned out both versions were wrong. The original was too blunt, because the output was actually safe, and the new one was too narrow, because it missed tricks like single quotes and encoded letters. Claude replaced it with a test that checks every real link against 15 different attacks, and then broke the sanitizer on purpose to prove the test actually fails when it should. The same thing happened again in T03 with the draft guard, where the first fix only checked post pages and not the home page.

**The New page button** 
This one I found myself. When I went back to add my chapter's real pages (History, Community Service, Contact), every one of them saved as a post and the pages table stayed empty. The "New page" button was opening the post form, because two routes had the same name and the posts one won. 188 tests passed the whole time, because the tests submitted the page form directly and never clicked the button. I also caught the live site saying "Knox County Historical Society" and "IPHS 400 Mini-Project #2" after T04, even though 96 tests passed and two reviewers looked at it.

**What I learned**
 A green test doesn't mean everything is good. A test can pass because it's checking the wrong thing. The bugs I found myself only showed up when I actually opened the site and used the CMS like an officer would.

## 3. Which skills I used, and why
**Planning** I used /grill-with-docs, then /to-spec, then /to-tickets. The grill asked me 21 questions about the fraternity and what I would like to showcase, but it sent them in batches of 6 to 8 instead of one at a time like the manual says, which made it easy to just say yes to everything. I tried to answer each one and overrode the ones that didn't fit my chapter. /to-spec turned that into issue #1, and /to-tickets broke it into 8 core tickets and 5 stretch tickets. I kept 8 core instead of the minimum 7 so I'd have some room, and later added T14 for the design, which made 9.

**One ticket per session** 
I ran /clear between every ticket so each one started fresh. I didn't want to have a problem with context rot. /implement ran /tdd and /code-review on its own, with one reviewer for code standards and one for the spec, and posted the findings on the issue before closing it. I didn't use /implement-spec even though it was faster, because it does the whole spec at once and skips the per-ticket reviews.

**What surprised me** 
A test that kept failing randomly turned out to be an actual bug. My laptop's clock sometimes jumped backwards a few seconds, so login cookies looked like they came from the future and people would randomly get logged out. Claude also mixed up ticket and issue numbers once (T05 is issue #6), so after that I told it the ticket number every time.
## 4. Budget, plan vs actual, and what I'd add next
**Plan vs actual** 
I planned for the grill, spec and tickets to take about 50% of a 5-hour window, and it only used 8%, mostly because the grill batched its questions. I planned about 12% per ticket including the review, and it was closer to 4%. I overestimated everything by 3 to 6 times, and the weekly cap barely moved. I only hit the 5-hour limit once, near the end during the design ticket. The first budget report also looked about 4 times worse than it really was, because the template came with someone else's usage data in it, which I had to delete.

**What I'd add next** 
The biggest gap is that our officers all use their own laptops, but the console only runs on one machine, so right now they'd have to come to my laptop to post. Remote access would fix that. I'd also build the stretch tickets I didn't get to (image uploads, the event date, backups and login lockout), make "New page" and "New post" easier to tell apart since even I mixed them up, and replace the raw CSRF error message with something a normal person would understand.