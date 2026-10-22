# Rights gate

Clear this before writing the treatment. It is cheaper to change the brief than
to rebuild a finished film.

## What must be cleared

| Material | Ask | If not cleared |
|---|---|---|
| Song master / recording | Did the user supply it, and may it be used in this film? | Do not use it. Ask for a track they own or a licensed instrumental. |
| Words and melody | Who wrote them? Is this a cover, a translation, or a lyric display? | Public release needs a lyric reprint / sync licence. |
| Character | Is it the user's original character, or a franchise character? | Design an original stand-in. Never use official art, sprites, logos, fonts, or voice clips. |
| Character reference image | Does the user own or have permission for the photo/illustration they handed over as a reference? | Do not ingest it. Describe the character in words and design from the description. If cleared: keep it in `character/`, use `char_ref.py` only to draft, redraw the sprite, disclose the reference in `CREDITS`, and never deliver the folder. |
| Voice | Is it the user's own voice, a hired voice, or a cloned voice? | Do not clone a real performer without written permission. |
| Fonts | GNU Unifont, a Google font, or a commercial font? | Record the licence and subset only what is used. |
| Palette / textures | Original, ENDESGA-32, or a scanned asset? | Credit it and check the licence for commercial use. |
| Footage / photos | User-owned, licensed, or found online? | Found online is not a licence. Draw a fictional stand-in. |

Fan work is not a blanket permission. A non-commercial fan film still uses the
song, the lyrics, and the character; public release normally needs the rights
holders' permission. Say this plainly in the handoff.

## CREDITS

`CREDITS` must name every third-party asset and its source and licence. The
template has sections for music, character, visuals, audio, and rights. The
`check_delivery.py` script fails when the rights section is missing.

## Generic notice template

Replace every bracketed field with the truth. Keep the substance: what was
used, who owns it, what permission covers it, and whether the film is an
unofficial fan work.

English:

> "[Song title]" — words and music by [writers], performed by [artist],
> recording owned by [label]. Used with permission for [scope / territory /
> duration]. [Character name] is owned by [rights holder]; this is an
> unofficial fan work, not endorsed by [rights holder]. No official artwork,
> logos, fonts, footage, or voice clips were used. Public release requires the
> user's own sync, master, lyric-reprint, and character licences.

Chinese:

> 本片使用 [歌曲名]（词曲：[词曲作者]；表演：[演唱者]；录音版权：[录音版权方]），
> 使用范围为 [范围]。片中 [角色名] 形象版权归 [权利人] 所有；本片为非官方同人作品，
> 不使用官方素材，不暗示与权利人的关联或背书。公开发布前请自行取得词曲、录音、
> 角色形象与音乐录音的使用授权。

If the work is fully original, replace the fan-work sentence with "All
characters and artwork are original." Do not copy a notice from another film;
the names and permission status must match this production.

## What this skill bundles

The skill contains code, templates, and documentation only. It does **not**
contain any song, lyrics, character drawings, voice stems, rendered frames, or
poster from a production. The example lyrics are original filler and must be
replaced.
