# CONTEXT.md glossary

The Chi Chapter of Delta Tau Delta at Kenyon College runs a small CMS: officers write content locally, and the president releases it to a public static site for prospective members, alumni, parents and Kenyon staff.

## Language

### People

**Officer**:
A chapter member who holds a position (president, secretary, social media chair, and so on) for a term. Officers change about once a year.
_Avoid_: Staff, member (a member need not hold a position)

**User**:
An Officer's login account in the CMS.
_Avoid_: Account, profile

**Temporary password**:
A password the Admin resets another User to, shown to the Admin once. The User must replace it with their own at next login. The Admin's own recovery is `cms reset-password`, which sets a password directly and is not temporary.
_Avoid_: Reset password, default password

**Admin**:
The role held by the president. Controls Users, Pages, navigation, and the final release to the public site.
_Avoid_: Superuser, owner

**Editor**:
The role held by the other Officers (secretary, social media chairs, alumni relations chair, community service chair). Writes their own Posts and edits Pages assigned to them.
_Avoid_: Contributor, author (author is a Post's creator, not a role)

**Deactivated**:
A User who can no longer log in. Their content and byline stay; the account is never deleted.
_Avoid_: Deleted, disabled, banned

**Term**:
The title and academic year an Officer served, such as "Secretary, 2026–27".
_Avoid_: Position, tenure

**Byline**:
The public attribution on a Post: the author's full name, title, and Term, fixed when the Post is first marked Published.
_Avoid_: Credit, author line

### Content

**Post**:
A dated news item written by one Editor or the Admin, listed in the public news feed.
_Avoid_: Article, update, entry

**Page**:
An undated, authorless piece of standing content (About, History, Community Service) that can appear in public navigation.
_Avoid_: Section

**Assigned editor**:
The one Editor, besides the Admin, who may edit a given Page.
_Avoid_: Page owner

**Draft**:
Content that has not been marked Published. Never leaves the database.
_Avoid_: Unpublished (ambiguous with unpublishing something that was live)

**Published**:
The status an Editor or Admin gives content to say it is ready to go public. It does not make the content Live.
_Avoid_: Live, released

**Live**:
Present on the public site as of the latest Deploy.
_Avoid_: Online, released

**Publish run**:
The Admin's `cms publish` step. It renders all Published content to the local static site, shows what is new, changed or removed, and refuses if any Draft would appear.
_Avoid_: Export, build

**Deploy**:
The Admin's `cms deploy` step. After the Admin confirms, it pushes the rendered static site to the public host, making its content Live.
_Avoid_: Release, push, upload

**Pending release**:
Published content that is not yet Live, or that has changed since the last Deploy.
_Avoid_: Queued, staged

**Navigation**:
The public site's top links: Home, the Pages marked to show in navigation in the Admin's chosen order, then News.
_Avoid_: Menu

**Slug**:
The URL-safe name of a Post or Page, unique within its kind and locked after first being Published.
_Avoid_: Permalink, URL name
