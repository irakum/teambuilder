import csv
import io
import os
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError, BusinessRuleError
from app.models.session import SessionStatus
from app.repositories.session import SessionRepository
from app.repositories.team import TeamRepository


class ExportService:
    def __init__(self, db: AsyncSession) -> None:
        self.session_repo = SessionRepository(db)
        self.team_repo = TeamRepository(db)

    async def _get_distributed_session(self, session_id: UUID):
        session = await self.session_repo.get(session_id)
        if session is None:
            raise NotFoundError(f"Сесію {session_id} не знайдено")
        if session.status != SessionStatus.distributed:
            raise BusinessRuleError("Експорт доступний лише після виконання розподілу")
        return session

    async def to_csv(self, session_id: UUID) -> bytes:
        await self._get_distributed_session(session_id)
        teams = await self.team_repo.list_by_session(session_id)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Команда", "Учасник", "Рейтинг команди"])

        for team in teams:
            for participant in team.participants:
                writer.writerow([
                    team.name,
                    participant.name,
                    f"{team.total_score:.1f}",
                ])

        return output.getvalue().encode("utf-8-sig")

    async def to_pdf(self, session_id: UUID) -> bytes:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
        ]
        font_name = "DejaVuSans"
        font_bold = "DejaVuSans-Bold"

        registered = False
        for path in font_paths:
            if os.path.exists(path):
                bold_path = path.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")
                pdfmetrics.registerFont(TTFont(font_name, path))
                if os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont(font_bold, bold_path))
                else:
                    font_bold = font_name
                registered = True
                break

        if not registered:
            font_name = "Helvetica"
            font_bold = "Helvetica-Bold"

        session = await self._get_distributed_session(session_id)
        teams = await self.team_repo.list_by_session(session_id)

        os.makedirs(settings.export_dir, exist_ok=True)
        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=2*cm, rightMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm,
        )

        title_style = ParagraphStyle("Title", fontName=font_bold, fontSize=16, spaceAfter=12, leading=20)
        team_style = ParagraphStyle("Team", fontName=font_bold, fontSize=13, spaceAfter=6, spaceBefore=12, leading=18)

        story = []
        story.append(Paragraph(f"Результати розподілу: {session.name}", title_style))
        story.append(Spacer(1, 0.5*cm))

        for team in teams:
            story.append(Paragraph(f"{team.name}  (рейтинг: {team.total_score:.1f})", team_style))
            table_data = [["Учасник", "Навички"]]
            for p in team.participants:
                skills_str = ", ".join(f"{ps.skill.name} ({ps.level})" for ps in p.skills) or "—"
                table_data.append([p.name, skills_str])

            t = Table(table_data, colWidths=[6*cm, 11*cm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E8E8")),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTNAME", (0, 0), (-1, 0), font_bold),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#AAAAAA")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.4*cm))

        doc.build(story)
        return buffer.getvalue()